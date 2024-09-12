import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from datetime import datetime
from openpyxl import Workbook


# Constants
ORDINARY_INTEREST_RATE = 0.10  # 10% monthly interest for ordinary loans
CREDIT_LINE10_INTEREST_RATE = 0.05  # 5% monthly interest for credit line loans
CREDIT_LINE20_INTEREST_RATE = 0.0325  # 3.25% monthly interest for credit line loans

def create_database():
    conn = sqlite3.connect('loans.db')
    cursor = conn.cursor()

    # Drop existing tables if they exist
    cursor.execute("DROP TABLE IF EXISTS clients")
    cursor.execute("DROP TABLE IF EXISTS payments")
    cursor.execute("DROP TABLE IF EXISTS loan_history")

    # # Create clients table
    cursor.execute('''CREATE TABLE clients (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        address TEXT,
                        phone TEXT,
                        loan_type TEXT NOT NULL,
                        balance REAL NOT NULL,
                        interest REAL NOT NULL)''')

    # # Create payments table
    cursor.execute('''CREATE TABLE payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id INTEGER,
                        amount REAL NOT NULL,
                        payment_date TEXT NOT NULL,
                        FOREIGN KEY (client_id) REFERENCES clients (id))''')

    # # Create loan history table
    cursor.execute('''CREATE TABLE loan_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id INTEGER,
                        action TEXT NOT NULL,
                        amount REAL NOT NULL,
                        date TEXT NOT NULL,
                        FOREIGN KEY (client_id) REFERENCES clients (id))''')

    conn.commit()
    conn.close()


def add_client():
    name = entry_name.get()
    address = entry_address.get()
    phone = entry_phone.get()
    loan_type = var_loan_type.get()

    # Definir el balance e interés según el tipo de préstamo
    if loan_type == "ordinary":
        balance = float(entry_balance.get())
        interest_rate = ORDINARY_INTEREST_RATE
    elif loan_type == "credit_line_10":
        balance = 10000
        interest_rate = CREDIT_LINE10_INTEREST_RATE
    elif loan_type == "credit_line_20":
        balance = 20000
        interest_rate = CREDIT_LINE20_INTEREST_RATE
    else:
        messagebox.showerror("Error", "Tipo de préstamo inválido.")
        return

    interest = balance * interest_rate

    conn = sqlite3.connect('loans.db')
    cursor = conn.cursor()

    cursor.execute("INSERT INTO clients (name, address, phone, loan_type, balance, interest) VALUES (?, ?, ?, ?, ?, ?)", 
                   (name, address, phone, loan_type, balance, interest))

    client_id = cursor.lastrowid

    cursor.execute("INSERT INTO loan_history (client_id, action, amount, date) VALUES (?, ?, ?, ?)",
                   (client_id, "Préstamo inicial", balance, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

    messagebox.showinfo("Cliente Agregado", f"Cliente {name} agregado con un préstamo inicial de ${balance:.2f}")
    clear_entry_fields()
    load_clients()


def load_clients():
    for i in tree.get_children():
        tree.delete(i)  # Clear the table

    conn = sqlite3.connect('loans.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM clients")
    clients = cursor.fetchall()

    for client in clients:
        tree.insert("", "end", values=(client[0], client[1], client[2], client[3], client[4], f"${client[5]:.2f}", f"${client[6]:.2f}"))

    conn.close()

def load_client_names():
    conn = sqlite3.connect('loans.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM clients")
    clients = cursor.fetchall()

    client_names = [f"{client[0]} - {client[1]}" for client in clients]  # Combinar ID y nombre
    conn.close()
    
    return client_names

def add_payment():
    try:
        client_id = int(entry_client_id.get())
        payment = float(entry_payment.get())

        conn = sqlite3.connect('loans.db')
        cursor = conn.cursor()

        cursor.execute("SELECT balance, interest, loan_type FROM clients WHERE id = ?", (client_id,))
        result = cursor.fetchone()

        if result is None:
            messagebox.showerror("Error", "Cliente no encontrado.")
            return

        balance, current_interest, loan_type = result

        # Ajustar la tasa de interés según el tipo de préstamo
        if loan_type == "ordinary":
            interest_rate = ORDINARY_INTEREST_RATE
        elif loan_type == "credit_line_10":
            interest_rate = CREDIT_LINE10_INTEREST_RATE
        elif loan_type == "credit_line_20":
            interest_rate = CREDIT_LINE20_INTEREST_RATE
        else:
            messagebox.showerror("Error", "Tipo de préstamo no válido.")
            return

        # Primero, pagar cualquier interés pendiente
        if payment >= current_interest:
            payment -= current_interest
            new_interest = 0
        else:
            new_interest = current_interest - payment
            payment = 0

        # Luego, reducir el balance principal
        if payment > 0:
            if payment >= balance:
                new_balance = 0
            else:
                new_balance = balance - payment
        else:
            new_balance = balance

        # Calcular nuevo interés basado en el nuevo balance
        new_interest += new_balance * interest_rate

        # Actualizar balance e interés del cliente
        cursor.execute("UPDATE clients SET balance = ?, interest = ? WHERE id = ?", (new_balance, new_interest, client_id))

        # Registrar el pago
        cursor.execute("INSERT INTO payments (client_id, amount, payment_date) VALUES (?, ?, ?)",
                       (client_id, float(entry_payment.get()), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()
        conn.close()

        messagebox.showinfo("Pago", f"Pago de ${float(entry_payment.get()):.2f} registrado para el cliente {client_id}")
        clear_entry_fields()
        load_clients()

    except ValueError:
        messagebox.showerror("Error", "Por favor ingresa un ID y un monto de pago válidos.")


def renew_or_increase_loan():
    try:
        client_id = int(entry_client_id.get())
        amount = float(entry_amount.get())
        action = var_loan_action.get()

        conn = sqlite3.connect('loans.db')
        cursor = conn.cursor()

        cursor.execute("SELECT balance, interest, loan_type FROM clients WHERE id = ?", (client_id,))
        result = cursor.fetchone()

        if result is None:
            messagebox.showerror("Error", "Cliente no encontrado.")
            return

        current_balance, current_interest, loan_type = result
        interest_rate = ORDINARY_INTEREST_RATE if loan_type == "ordinary" else CREDIT_LINE_INTEREST_RATE

        if action == "renew":
            new_balance = current_balance
            new_interest = current_interest
        elif action == "increase":
            new_balance = current_balance + amount
            new_interest = current_interest + (amount * interest_rate)

        cursor.execute("UPDATE clients SET balance = ?, interest = ? WHERE id = ?", (new_balance, new_interest, client_id))

        # Record the action in loan history
        cursor.execute("INSERT INTO loan_history (client_id, action, amount, date) VALUES (?, ?, ?, ?)",
                       (client_id, "Renovación" if action == "renew" else "Aumento", amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()
        conn.close()

        messagebox.showinfo("Préstamo Actualizado", f"Préstamo {'renovado' if action == 'renew' else 'aumentado'} para el cliente {client_id}")
        clear_entry_fields()
        load_clients()

    except ValueError:
        messagebox.showerror("Error", "Por favor ingresa un ID y un monto válidos.")

def view_client_history():
    try:
        client_id = int(entry_client_id.get())

        conn = sqlite3.connect('loans.db')
        cursor = conn.cursor()

        # Get client info
        cursor.execute("SELECT name FROM clients WHERE id = ?", (client_id,))
        client_name = cursor.fetchone()[0]

        # Get payment history
        cursor.execute("SELECT amount, payment_date FROM payments WHERE client_id = ? ORDER BY payment_date DESC", (client_id,))
        payments = cursor.fetchall()

        # Get loan history
        cursor.execute("SELECT action, amount, date FROM loan_history WHERE client_id = ? ORDER BY date DESC", (client_id,))
        loan_history = cursor.fetchall()

        conn.close()

        # Create a new window to display the history
        history_window = tk.Toplevel(root)
        history_window.title(f"Historial del Cliente: {client_name}")

        # Create a notebook (tabs)
        notebook = ttk.Notebook(history_window)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Payments tab
        payments_frame = ttk.Frame(notebook)
        notebook.add(payments_frame, text="Pagos")

        payments_tree = ttk.Treeview(payments_frame, columns=("Monto", "Fecha"), show="headings")
        payments_tree.heading("Monto", text="Monto")
        payments_tree.heading("Fecha", text="Fecha")
        payments_tree.pack(fill=tk.BOTH, expand=True)

        for payment in payments:
            payments_tree.insert("", "end", values=(f"${payment[0]:.2f}", payment[1]))

        # Loan History tab
        loan_history_frame = ttk.Frame(notebook)
        notebook.add(loan_history_frame, text="Historial de Préstamos")

        loan_history_tree = ttk.Treeview(loan_history_frame, columns=("Acción", "Monto", "Fecha"), show="headings")
        loan_history_tree.heading("Acción", text="Acción")
        loan_history_tree.heading("Monto", text="Monto")
        loan_history_tree.heading("Fecha", text="Fecha")
        loan_history_tree.pack(fill=tk.BOTH, expand=True)

        for action in loan_history:
            loan_history_tree.insert("", "end", values=(action[0], f"${action[1]:.2f}", action[2]))

    except ValueError:
        messagebox.showerror("Error", "Por favor ingresa un ID de cliente válido.")

def clear_entry_fields():
    entry_name.delete(0, tk.END)
    entry_address.delete(0, tk.END)
    entry_phone.delete(0, tk.END)
    entry_balance.delete(0, tk.END)
    entry_client_id.delete(0, tk.END)
    entry_payment.delete(0, tk.END)
    entry_amount.delete(0, tk.END)


def generate_excel_report():
    conn = sqlite3.connect('loans.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM clients")
    clients = cursor.fetchall()

    # Crear un libro de trabajo de Excel
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Reporte de Préstamos"

    # Agregar encabezados
    headers = ["ID", "Nombre", "Dirección", "Teléfono", "Tipo de Préstamo", "Balance", "Interés"]
    sheet.append(headers)

    total_balance = 0
    total_interest = 0

    for client in clients:
        sheet.append([client[0], client[1], client[2], client[3], client[4], client[5], client[6]])
        total_balance += client[5]
        total_interest += client[6]

    # Agregar fila de totales
    sheet.append(["", "", "", "", "Totales", total_balance, total_interest])

    # Guardar el archivo de Excel
    report_path = os.path.join(os.getcwd(), 'reporte_prestamos.xlsx')
    workbook.save(report_path)
    conn.close()

    messagebox.showinfo("Reporte Generado", f"Reporte Excel generado en: {report_path}")

def update_balance_based_on_loan_type():
    loan_type = var_loan_type.get()
    if loan_type == "credit_line_10":
        entry_balance.delete(0, tk.END)
        entry_balance.insert(0, "10000")
    elif loan_type == "credit_line_20":
        entry_balance.delete(0, tk.END)
        entry_balance.insert(0, "20000")
    else:
        entry_balance.delete(0, tk.END)  # Si es ordinario, dejamos el campo vacío para ingreso manual


# Create the main window
root = tk.Tk()
root.title("Sistema de Administración de Credito")

# Create tabs
notebook = ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=True)

# Client Management Tab
client_frame = ttk.Frame(notebook)
notebook.add(client_frame, text="Gestión de Clientes")

# Client Information Fields
ttk.Label(client_frame, text="Nombre:").grid(row=0, column=0, padx=5, pady=5)
entry_name = ttk.Entry(client_frame, width=50)  
entry_name.grid(row=0, column=1, padx=5, pady=5)  

ttk.Label(client_frame, text="Dirección:").grid(row=1, column=0, padx=5, pady=5)
entry_address = ttk.Entry(client_frame, width=50)  
entry_address.grid(row=1, column=1, padx=5, pady=5)

ttk.Label(client_frame, text="Teléfono:").grid(row=2, column=0, padx=5, pady=5)
entry_phone = ttk.Entry(client_frame, width=50)  
entry_phone.grid(row=2, column=1, padx=5, pady=5)


# Crear un frame para agrupar los botones de radio del tipo de préstamo
loan_type_frame = ttk.Frame(client_frame)
loan_type_frame.grid(row=3, column=1, columnspan=3, padx=5, pady=5)

ttk.Label(client_frame, text="Tipo de Préstamo:").grid(row=3, column=0, padx=5, pady=5)
var_loan_type = tk.StringVar(value="ordinary")

# Asociar los botones de radio con la función de autocompletado
ttk.Radiobutton(loan_type_frame, text="Ordinario", variable=var_loan_type, value="ordinary", command=update_balance_based_on_loan_type).grid(row=0, column=0, padx=10, pady=5)
ttk.Radiobutton(loan_type_frame, text="Línea de Crédito 10", variable=var_loan_type, value="credit_line_10", command=update_balance_based_on_loan_type).grid(row=0, column=1, padx=10, pady=5)
ttk.Radiobutton(loan_type_frame, text="Línea de Crédito 20", variable=var_loan_type, value="credit_line_20", command=update_balance_based_on_loan_type).grid(row=0, column=2, padx=10, pady=5)

# Campo de Monto del Préstamo
ttk.Label(client_frame, text="Monto del Préstamo:").grid(row=4, column=0, padx=5, pady=5)
entry_balance = ttk.Entry(client_frame, width=50)
entry_balance.grid(row=4, column=1, padx=5, pady=5)

ttk.Button(client_frame, text="Agregar Cliente", command=add_client).grid(row=5, column=0, columnspan=3, pady=10)

# Client List
tree = ttk.Treeview(client_frame, columns=("ID", "Nombre", "Dirección", "Teléfono", "Tipo", "Balance", "Interés"), show="headings")
tree.heading("ID", text="ID")
tree.heading("Nombre", text="Nombre")
tree.heading("Dirección", text="Dirección")
tree.heading("Teléfono", text="Teléfono")
tree.heading("Tipo", text="Tipo de Préstamo")
tree.heading("Balance", text="Balance")
tree.heading("Interés", text="Interés")
tree.grid(row=6, column=0, columnspan=3, padx=5, pady=5)

# Payment and Loan Management Tab

management_frame = ttk.Frame(notebook)
notebook.add(management_frame, text="Gestión de Pagos y Préstamos")

ttk.Label(management_frame, text="ID del Cliente:").grid(row=0, column=0, padx=5, pady=5)
entry_client_id = ttk.Entry(management_frame)
entry_client_id.grid(row=0, column=1, padx=5, pady=5)

ttk.Label(management_frame, text="Monto:").grid(row=1, column=0, padx=5, pady=5)
entry_payment = ttk.Entry(management_frame)
entry_payment.grid(row=1, column=1, padx=5, pady=5)

ttk.Button(management_frame, text="Registrar Pago", command=add_payment).grid(row=2, column=0, columnspan=2, pady=10)

ttk.Label(management_frame, text="Acción de Préstamo:").grid(row=3, column=0, padx=5, pady=5)
var_loan_action = tk.StringVar(value="renew")
ttk.Radiobutton(management_frame, text="Renovar", variable=var_loan_action, value="renew").grid(row=3, column=1, padx=5, pady=5)
ttk.Radiobutton(management_frame, text="Aumentar", variable=var_loan_action, value="increase").grid(row=3, column=2, padx=5, pady=5)

ttk.Label(management_frame, text="Monto (para aumento):").grid(row=4, column=0, padx=5, pady=5)
entry_amount = ttk.Entry(management_frame)
entry_amount.grid(row=4, column=1, padx=5, pady=5)

ttk.Button(management_frame, text="Procesar Acción de Préstamo", command=renew_or_increase_loan).grid(row=5, column=0, columnspan=3, pady=10)

ttk.Button(management_frame, text="Ver Historial del Cliente", command=view_client_history).grid(row=6, column=0, columnspan=3, pady=10)

# Report Generation
ttk.Button(root, text="Generar Reporte Excel", command=generate_excel_report).pack(pady=10)

# Initialize the database
create_database()

# Load initial client list
load_clients()

# Start the main event loop
root.mainloop()
