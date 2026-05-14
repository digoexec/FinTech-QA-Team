import sqlite3
import re
import requests
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "fintech_qa_secret"

def init_db():
    conn = sqlite3.connect('fintech.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        email TEXT UNIQUE, 
        password TEXT,
        is_admin INTEGER DEFAULT 0)''') # 0 = Usuário, 1 = Admin
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, 
        type TEXT, 
        amount REAL, 
        description TEXT, 
        FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

def get_currency_rates():
    try:
        response = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL")
        data = response.json()
        return {"USD": float(data['USDBRL']['bid']), "EUR": float(data['EURBRL']['bid'])}
    except:
        return {"USD": 0.0, "EUR": 0.0}

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not is_valid_email(email):
            flash("Erro: E-mail inválido", "error")
            return render_template('register.html')
            
        try:
            conn = sqlite3.connect('fintech.db')
            c = conn.cursor()
            c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
            conn.commit()
            conn.close()
            flash("Conta criada com sucesso! Faça login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Erro: Usuário já existe", "error")
            
    return render_template('register.html')

@app.route('/admin')
def admin_panel():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Verifica se o usuário logado é admin
    conn = sqlite3.connect('fintech.db')
    c = conn.cursor()
    c.execute("SELECT is_admin FROM users WHERE id=?", (session['user_id'],))
    user = c.fetchone()
    
    if not user or user[0] != 1:
        flash("Acesso negado: Você não é um administrador.", "error")
        return redirect(url_for('dashboard'))
    
    # Busca todos os usuários e estatísticas
    c.execute("SELECT id, email, is_admin FROM users")
    all_users = c.fetchall()
    c.execute("SELECT COUNT(*) FROM transactions")
    total_transacoes = c.fetchone()[0]
    conn.close()
    
    return render_template('admin.html', users=all_users, total_transacoes=total_transacoes)

@app.route('/admin/delete_user/<int:u_id>', methods=['POST'])
def delete_user(u_id):
    # (Adicionar verificação de admin aqui também por segurança)
    conn = sqlite3.connect('fintech.db')
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE user_id=?", (u_id,))
    c.execute("DELETE FROM users WHERE id=?", (u_id,))
    conn.commit()
    conn.close()
    flash("Usuário removido do sistema.", "success")
    return redirect(url_for('admin_panel'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = sqlite3.connect('fintech.db')
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            flash("Erro: Credenciais incorretas", "error")
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = sqlite3.connect('fintech.db')
    c = conn.cursor()
    c.execute("SELECT id, type, amount, description FROM transactions WHERE user_id=?", (user_id,))
    transactions = c.fetchall()
    conn.close()
    
    saldo = sum([t[2] if t[1] == 'receita' else -t[2] for t in transactions])
    rates = get_currency_rates()
    
    return render_template('dashboard.html', saldo=saldo, transactions=transactions, rates=rates)

@app.route('/transaction', methods=['POST'])
def add_transaction():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    t_type = request.form.get('type')
    amount = float(request.form.get('amount'))
    description = request.form.get('description')
    
    if amount < 0:
        flash("Erro: O valor não pode ser negativo", "error")
        return redirect(url_for('dashboard'))
        
    conn = sqlite3.connect('fintech.db')
    c = conn.cursor()
    c.execute("INSERT INTO transactions (user_id, type, amount, description) VALUES (?, ?, ?, ?)", (user_id, t_type, amount, description))
    conn.commit()
    conn.close()
    flash("Transação adicionada com sucesso!", "success")
    return redirect(url_for('dashboard'))

@app.route('/transaction/delete/<int:t_id>', methods=['POST'])
def delete_transaction(t_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('fintech.db')
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (t_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Transação excluída!", "success")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)