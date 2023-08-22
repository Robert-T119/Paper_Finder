from openai.embeddings_utils import cosine_similarity
import pandas as pd
import threading
import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedTk
from tkinter import PhotoImage
import queue
import datetime

from data_fetching import get_total_papers_for_period, extract_papers_from_openalex_search, generate_date_ranges, abstract_from_inverted_index, remove_non_printable_chars
from text_processing import clean_text, lowercase_text, tokenize_text, remove_stopwords, lemmatize_tokens, is_relevant, run_prediction, get_embedding
from gui import show_data, on_mousewheel,update_progress_bar
from constants import concept_list

update_queue = queue.Queue()

# Functions
def execute_script(canvas, progress_var, progress_percentage_label):
    # Disable the button while processing
    execute_button.config(state=tk.DISABLED)
    status_label.config(text="Processing...")

    try:
        selected_concept_names = [concept_id_entry.get(idx) for idx in concept_id_entry.curselection()]
        selected_concept_ids = [url for name, url in concept_list if name in selected_concept_names]

        from_publication_date = from_publication_date_entry.get()
        to_publication_date = to_publication_date_entry.get()
        target_embedding_word = target_embedding_word_entry.get()

        papers_fetched_so_far = 0  # Counter to keep track of the total papers fetched so far
        # Fetch the total number of papers for the entire period for all selected concepts
        total_papers_for_period = sum([get_total_papers_for_period(from_publication_date, to_publication_date, concept_id) for concept_id in selected_concept_ids])
        print(f"Total papers for entire period: {total_papers_for_period}")  # Debug print

        total_days = (datetime.datetime.strptime(to_publication_date, "%Y-%m-%d") - datetime.datetime.strptime(from_publication_date, "%Y-%m-%d")).days
        print(f"Fetching papers for {total_days} days...")

        papers = []
        limit = 100000
        for concept_id in selected_concept_ids:
            for date in generate_date_ranges(from_publication_date, to_publication_date):
                current_date_label.config(text=f"Fetching papers for {date}...")
                
                search_url = f'https://api.openalex.org/works?filter=concept.id:{concept_id},from_publication_date:{date},to_publication_date:{date}&sort=publication_date:desc'
                papers_for_current_date = extract_papers_from_openalex_search(search_url, limit, date)

                papers_fetched_so_far += len(papers_for_current_date)
                progress_percentage = (float(papers_fetched_so_far) / float(total_papers_for_period)) * 100
                
                update_progress_bar(progress_percentage, progress_var, progress_percentage_label)
                root.update()
                progress_bar.update_idletasks()
                
                print(f"Total papers fetched so far: {papers_fetched_so_far}")
                print(f"Papers fetched for {date}: {len(papers_for_current_date)}")
                print(f"Progress: {progress_percentage:.2f}% of papers fetched for the entire period")
                
                papers.extend(papers_for_current_date)

        update_progress_bar(100, progress_var, progress_percentage_label)

        df = pd.DataFrame(papers, columns=["DOI", "Title", "Authors", "Publication Date", "Abstract", "Concepts"])
        df['Cleaned Abstract'] = df['Abstract'].apply(clean_text).apply(lowercase_text)
        df['Tokens'] = df['Cleaned Abstract'].apply(tokenize_text).apply(remove_stopwords).apply(lemmatize_tokens)
        df['Is Relevant'] = df['Cleaned Abstract'].apply(is_relevant)
        sofc_relevant_papers = df[df['Is Relevant']]
        separator = "\n\n###\n\n"
        sofc_model_name = "ada:ft-personal-2023-07-29-19-02-14"
        sofc_predictions = run_prediction(sofc_model_name, sofc_relevant_papers['Cleaned Abstract'] + separator)
        sofc_relevant_papers['SOFC Predictions'] = sofc_predictions
        sofc_positive_papers = sofc_relevant_papers[sofc_relevant_papers['SOFC Predictions'] == 'positive']
        sofc_materials_model_name = "ada:ft-personal-2023-07-27-12-26-20"
        sofc_materials_predictions = run_prediction(sofc_materials_model_name, sofc_positive_papers['Cleaned Abstract'] + separator)
        sofc_positive_papers['SOFC Materials Predictions'] = sofc_materials_predictions
        target_embedding = get_embedding(target_embedding_word)
        sofc_positive_papers['embedding'] = sofc_positive_papers['Abstract'].apply(get_embedding)
        sofc_positive_papers['similarity_score'] = sofc_positive_papers['embedding'].apply(lambda x: cosine_similarity(x, target_embedding))
        sofc_positive_papers = sofc_positive_papers.sort_values('similarity_score', ascending=False)
        sofc_positive_papers = sofc_positive_papers[["DOI", "Title", "SOFC Predictions", "SOFC Materials Predictions", "similarity_score"]]
        print(sofc_positive_papers)
        sofc_positive_papers.to_excel('output.xlsx', index=False)

        # Update the status label when done
        status_label.config(text="Execution complete!")
        # Re-enable the button
        execute_button.config(state=tk.NORMAL)
        show_data(sofc_positive_papers, main_frame,root)
        canvas.configure(scrollregion=canvas.bbox("all"))
        
    except Exception as e:
        print(f"Error during execution: {e}")
        status_label.config(text=f"Error: {e}")
        # Re-enable the button in case of an error
        execute_button.config(state=tk.NORMAL)

def check_queue():
    try:
        progress = update_queue.get_nowait()
        update_progress_bar(progress)
        print(f"Progress from queue: {progress}")
    except queue.Empty:
        pass
    root.after(1000, check_queue)  # Check the queue every 100 milliseconds

# GUI code
root = ThemedTk(theme="aquotivo")  # Use the 'arc' theme
def on_root_right_click(event):
    print("Root window right-clicked!")

root.bind("<Button-3>", on_root_right_click)

root.title("Recent Paper Finder")
root.geometry("800x400")  # Adjust dimensions as needed
logo = PhotoImage(file="Pictures//logo.png")
root.iconphoto(False, logo)
root.bind_all("<MouseWheel>", lambda event: on_mousewheel(event, canvas))

# Create a canvas and add a scrollbar
canvas = tk.Canvas(root)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

vsb = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
vsb.pack(side=tk.RIGHT, fill=tk.Y)
canvas.configure(yscrollcommand=vsb.set)

canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

# Create a main frame inside the canvas
main_frame = ttk.Frame(canvas)
canvas.create_window((0, 0), window=main_frame, anchor="nw")

# Input Frame
input_frame = ttk.Frame(main_frame, padding="50 5 5 5")
input_frame.grid(row=0, column=0, sticky=tk.W+tk.E)

additional_image = PhotoImage(file="Pictures//picture.png")
resized_image = additional_image.subsample(2, 2)
additional_image_label = ttk.Label(input_frame, image=resized_image)
additional_image_label.grid(row=0, column=4, rowspan=5, padx=15, pady=5)

listbox_frame = ttk.Frame(input_frame)
listbox_frame.grid(row=0,column=1,sticky=tk.E, padx=5, pady=5)

concept_id_label = ttk.Label(input_frame, text="Select Concept(s):")
concept_id_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

concept_names_var = tk.StringVar(value=[x[0] for x in concept_list])
concept_id_entry = tk.Listbox(listbox_frame, listvariable=concept_names_var, selectmode=tk.MULTIPLE,height=4, width=25)
concept_id_entry.pack(side=tk.LEFT,fill=tk.Y)

scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=concept_id_entry.yview)
scrollbar.pack(side=tk.LEFT, fill=tk.Y)
concept_id_entry['yscrollcommand'] = scrollbar.set

from_publication_date_label = ttk.Label(input_frame, text="Enter From Publication Date (YYYY-MM-DD):")
from_publication_date_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
from_publication_date_entry = ttk.Entry(input_frame)
from_publication_date_entry.grid(row=1, column=1, sticky=tk.E, padx=5, pady=5)

to_publication_date_label = ttk.Label(input_frame, text="Enter To Publication Date (YYYY-MM-DD):")
to_publication_date_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
to_publication_date_entry = ttk.Entry(input_frame)
to_publication_date_entry.grid(row=2, column=1, sticky=tk.E, padx=5, pady=5)

target_embedding_word_label = ttk.Label(input_frame, text="Enter Target Embedding Word:")
target_embedding_word_label.grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
target_embedding_word_entry = ttk.Entry(input_frame)
target_embedding_word_entry.grid(row=3, column=1, sticky=tk.E, padx=5, pady=5)

# Execute Button and Status Label
execute_button = ttk.Button(main_frame, text="Execute Script", command=lambda: threading.Thread(target=execute_script, args=(canvas, progress_var, progress_percentage_label)).start())
execute_button.grid(row=1, column=0, pady=10)

# Status Label to show which date is currently being processed
current_date_label = ttk.Label(main_frame, text="")
current_date_label.grid(row=2, column=0, pady=10)

status_label = ttk.Label(main_frame, text="")
status_label.grid(row=3, column=0, pady=10)

# Progress Bar
progress_var = tk.DoubleVar()  # Variable to update the progress bar
progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=300, variable=progress_var, mode="determinate", maximum=100)
progress_bar.grid(row=4, column=0, pady=10)

progress_percentage_label = ttk.Label(main_frame, text="0%")
progress_percentage_label.grid(row=4, column=1)

check_queue()
root.mainloop()