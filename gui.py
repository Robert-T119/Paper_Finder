import tkinter as tk
from tkinter import ttk

def show_data(data_frame, main_frame,root):
    # Create a new frame for the table
    table_frame = ttk.Frame(main_frame)
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
    adjust_column_width(tree, data_frame.columns)

    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

    def on_treeview_click(event):
        print("Treeview clicked!")

    tree.bind("<Button-1>", on_treeview_click)


    # Right-click context menu
    context_menu = tk.Menu(tree, tearoff=0)
    context_menu.add_command(label="Copy", command=lambda: copy_to_clipboard(tree, root))

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

def on_mousewheel(event, canvas):
    canvas.yview_scroll(-1*(event.delta//120), "units")

def copy_to_clipboard(tree, root):
    selected_item = tree.selection()[0]  # Get selected item
    col_id = tree.identify_column(tree.winfo_pointerx() - tree.winfo_rootx())
    col_name = tree.heading(col_id, option="text")
    value = tree.set(selected_item, col_name)
    root.clipboard_clear()
    root.clipboard_append(value)
    root.update()  # This is necessary to finalize the clipboard action

def adjust_column_width(tree, columns, width=100):
    for col in columns:
        tree.column(col, width=width)

def update_progress_bar(percentage, progress_var, progress_percentage_label):
    progress_var.set(percentage)
    progress_percentage_label.config(text=f"{int(percentage)}%")