import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedTk
from tkinter import PhotoImage
import queue
from Constants import concept_list
import threading

class GUI:
        def __init__(self, execute_script):
                # Initializing attributes
                self.update_queue = queue.Queue()
                self.root = None
                self.execute_script = execute_script

                self.execute_button = None
                self.canvas = None
                self.progress_percentage_label = None
                self.current_date_label = None
                self.progress_bar = None
                self.status_label = None
                self.concept_id_entry = None
                self.from_publication_date_entry = None
                self.to_publication_date_entry = None
                self.target_embedding_word_entry = None
                self.main_frame = None
                self.additional_image = None
                self.resized_image = None

                self.initialize_gui()

        def show_data(self, data_frame, main_frame, root):
                # Create a new frame for the table
                table_frame = ttk.Frame(self.main_frame)
                table_frame.grid(row=3, column=0, sticky=tk.W+tk.E)

                # Create a treeview widget
                tree = ttk.Treeview(table_frame, columns=data_frame.columns.tolist(), show='headings')

                # Create scrollbars
                vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
                vsb.pack(side=tk.RIGHT, fill=tk.Y)
                hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)  # Horizontal Scrollbar
                hsb.pack(side=tk.BOTTOM, fill=tk.X)

                tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)  # Link the horizontal scrollbar to the tree

                # Create the columns
                for col in data_frame.columns:
                        tree.column(col, anchor=tk.W, width=150, stretch=tk.YES)  # Set stretch=tk.YES to make the column resizable
                        tree.heading(col, text=col, anchor=tk.W)

                # Insert the data
                for index, row in data_frame.iterrows():
                        tree.insert("", index, values=row.tolist())

                # Adjust column widths
                self.adjust_column_width(tree, data_frame.columns)

                tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

                def on_treeview_click(event):
                        print("Treeview clicked!")

                tree.bind("<Button-1>", on_treeview_click)

                # Right-click context menu
                context_menu = tk.Menu(tree, tearoff=0)
                context_menu.add_command(label="Copy", command=lambda: self.copy_to_clipboard(tree))

                def display_context_menu(event):
                        tree.selection_set(tree.identify_row(event.y))
                        print("Right-click detected!")  # Debugging print statement
                        context_menu.post(event.x_root, event.y_root)

                tree.bind("<Button-2>", display_context_menu)  # Bind right-click

                class ToolTip(object):
                        def __init__(self, widget):
                                self.widget = widget
                                self.tipwindow = None
                                self.id = None
                                self.x = self.y = 0

                        def showtip(self, text):
                                self.text = text
                                if self.tipwindow or not self.text:
                                        return
                                x = self.widget.winfo_pointerx()
                                y = self.widget.winfo_pointery() + 20
                                self.tipwindow = tw = tk.Toplevel(self.widget)
                                tw.wm_overrideredirect(1)
                                tw.wm_geometry("+%d+%d" % (x, y))
                                label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                                                background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                                                font=("tahoma", "8", "normal"))
                                label.pack(ipadx=1)
                        
                        def hidetip(self):
                            tw = self.tipwindow
                            self.tipwindow = None
                            if tw:
                                tw.destroy()

                tooltip = ToolTip(tree)

                def motion(event):
                        row_id = tree.identify_row(event.y)
                        col_id = tree.identify_column(event.x)

                        if row_id and col_id:
                                cell_text = tree.set(row_id, col_id)
                                tooltip.showtip(cell_text)
                        else:
                                tooltip.hidetip()

                tree.bind('<Motion>', motion)
                tree.bind('<Leave>', lambda e: tooltip.hidetip())


        def on_mousewheel(self, event):
                self.canvas.yview_scroll(-1*(event.delta//120), "units")


        def copy_to_clipboard(self, tree):
                selected_item = tree.selection()[0]  # Get selected item
                col_id = tree.identify_column(tree.winfo_pointerx() - tree.winfo_rootx())
                col_name = tree.heading(col_id, option="text")
                value = tree.set(selected_item, col_name)
                self.root.clipboard_clear()
                self.root.clipboard_append(value)
                self.root.update()  # This is necessary to finalize the clipboard action


        def adjust_column_width(self, tree, columns, width=100):
                for col in columns:
                        tree.column(col, width=width)

        def update_progress_bar(self, percentage, progress_var, progress_percentage_label):
            self.progress_var.set(percentage)
            self.progress_percentage_label.config(text=f"{int(percentage)}%")

        def check_queue(self):
                try:
                        progress = self.update_queue.get_nowait()
                        self.update_progress_bar(progress)
                        print(f"Progress from queue: {progress}")
                except queue.Empty:
                        pass
                self.root.after(100, self.check_queue)

        def initialize_gui(self):
                self.root = ThemedTk(theme="aquotivo")  # Use the 'arc' theme

                def on_root_right_click(event):
                        print("Root window right-clicked!")

                self.root.bind("<Button-3>", on_root_right_click)

                self.root.title("Recent Paper Finder")
                self.root.geometry("800x400")  # Adjust dimensions as needed
                logo = PhotoImage(file="Pictures//logo.png")
                self.root.iconphoto(False, logo)
                self.root.bind_all("<MouseWheel>", lambda event: self.on_mousewheel(event)) # Assuming on_mousewheel is defined

                # Create a canvas and add a scrollbar
                self.canvas = tk.Canvas(self.root)
                self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

                vsb = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
                vsb.pack(side=tk.RIGHT, fill=tk.Y)
                self.canvas.configure(yscrollcommand=vsb.set)

                self.canvas.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

                # Create a main frame inside the canvas
                self.main_frame = ttk.Frame(self.canvas)
                self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")

                # Input Frame
                input_frame = ttk.Frame(self.main_frame, padding="50 5 5 5")
                input_frame.grid(row=0, column=0, sticky=tk.W+tk.E)

                self.additional_image = PhotoImage(file="Pictures//picture.png")
                self.resized_image = self.additional_image.subsample(2, 2)
                additional_image_label = ttk.Label(input_frame, image=self.resized_image)
                additional_image_label.grid(row=0, column=4, rowspan=5, padx=15, pady=5)
                self.root.update_idletasks()

                listbox_frame = ttk.Frame(input_frame)
                listbox_frame.grid(row=0,column=1,sticky=tk.E, padx=5, pady=5)

                concept_id_label = ttk.Label(input_frame, text="Select Concept(s):")
                concept_id_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

                concept_names_var = tk.StringVar(value=[x[0] for x in concept_list])
                self.concept_id_entry = tk.Listbox(listbox_frame, listvariable=concept_names_var, selectmode=tk.MULTIPLE,height=4, width=25)
                self.concept_id_entry.pack(side=tk.LEFT,fill=tk.Y)

                scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.concept_id_entry.yview)
                scrollbar.pack(side=tk.LEFT, fill=tk.Y)
                self.concept_id_entry['yscrollcommand'] = scrollbar.set

                from_publication_date_label = ttk.Label(input_frame, text="Enter From Publication Date (YYYY-MM-DD):")
                from_publication_date_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
                self.from_publication_date_entry = ttk.Entry(input_frame)
                self.from_publication_date_entry.grid(row=1, column=1, sticky=tk.E, padx=5, pady=5)

                to_publication_date_label = ttk.Label(input_frame, text="Enter To Publication Date (YYYY-MM-DD):")
                to_publication_date_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
                self.to_publication_date_entry = ttk.Entry(input_frame)
                self.to_publication_date_entry.grid(row=2, column=1, sticky=tk.E, padx=5, pady=5)

                target_embedding_word_label = ttk.Label(input_frame, text="Enter Target Embedding Word:")
                target_embedding_word_label.grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
                self.target_embedding_word_entry = ttk.Entry(input_frame)
                self.target_embedding_word_entry.grid(row=3, column=1, sticky=tk.E, padx=5, pady=5)

                # Execute Button and Status Label
                self.execute_button = ttk.Button(self.main_frame, text="Execute Script", command=lambda: threading.Thread(target=self.execute_script).start())
                self.execute_button.grid(row=1, column=0, pady=10)

                # Status Label to show which date is currently being processed
                self.current_date_label = ttk.Label(self.main_frame, text="")
                self.current_date_label.grid(row=2, column=0, pady=10)

                self.status_label = ttk.Label(self.main_frame, text="")
                self.status_label.grid(row=3, column=0, pady=10)

                # Progress Bar
                self.progress_var = tk.DoubleVar()  # Variable to update the progress bar
                self.progress_bar = ttk.Progressbar(self.main_frame, orient="horizontal", length=300, variable=self.progress_var, mode="determinate", maximum=100)
                self.progress_bar.grid(row=4, column=0, pady=10)

                self.progress_percentage_label = ttk.Label(self.main_frame, text="0%")
                self.progress_percentage_label.grid(row=4, column=1)

                self.check_queue()

                return self.root, self.execute_button, self.canvas, self.progress_percentage_label, self.current_date_label, self.progress_bar, self.status_label, self.concept_id_entry, self.from_publication_date_entry, self.to_publication_date_entry, self.target_embedding_word_entry, self.main_frame, self.additional_image, self.resized_image