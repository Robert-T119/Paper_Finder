from openai.embeddings_utils import cosine_similarity
import pandas as pd
import tkinter as tk
import datetime

from Data_Fetching import get_total_papers_for_period, extract_papers_from_openalex_search, generate_date_ranges
from Text_Processing import clean_text, lowercase_text, tokenize_text, remove_stopwords, lemmatize_tokens, is_relevant, run_prediction, get_embedding
from Gui import GUI
from Constants import concept_list

# Functions
def execute_script():
    # Disable the button while processing
    app.execute_button.config(state=tk.DISABLED)
    app.status_label.config(text="Processing...")

    try:
        selected_concept_names = [app.concept_id_entry.get(idx) for idx in app.concept_id_entry.curselection()]
        selected_concept_ids = [url for name, url in concept_list if name in selected_concept_names]

        from_publication_date = app.from_publication_date_entry.get()
        to_publication_date = app.to_publication_date_entry.get()
        target_embedding_word = app.target_embedding_word_entry.get()

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
                app.current_date_label.config(text=f"Fetching papers for {date}...")
                
                search_url = f'https://api.openalex.org/works?filter=concept.id:{concept_id},from_publication_date:{date},to_publication_date:{date}&sort=publication_date:desc'
                papers_for_current_date = extract_papers_from_openalex_search(search_url, limit, date)

                papers_fetched_so_far += len(papers_for_current_date)
                progress_percentage = (float(papers_fetched_so_far) / float(total_papers_for_period)) * 100
                
                app.update_progress_bar(progress_percentage, app.progress_var, app.progress_percentage_label)
                app.root.update()
                app.progress_bar.update_idletasks()
                
                print(f"Total papers fetched so far: {papers_fetched_so_far}")
                print(f"Papers fetched for {date}: {len(papers_for_current_date)}")
                print(f"Progress: {progress_percentage:.2f}% of papers fetched for the entire period")
                
                papers.extend(papers_for_current_date)

        app.update_progress_bar(100, app.progress_var, app.progress_percentage_label)

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
        app.status_label.config(text="Execution complete!")
        # Re-enable the button
        app.execute_button.config(state=tk.NORMAL)
        app.show_data(sofc_positive_papers, app.main_frame,app.root)
        app.canvas.configure(scrollregion=app.canvas.bbox("all"))
        
    except Exception as e:
        print(f"Error during execution: {e}")
        app.status_label.config(text=f"Error: {e}")
        # Re-enable the button in case of an error
        app.execute_button.config(state=tk.NORMAL)

if __name__ == "__main__":
    app = GUI(execute_script)
    app.root.mainloop()