import pytest
import sqlite3
from app import app, init_db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # Usa um banco em memória para testes, ou reseta o atual
    init_db()
    with app.test_client() as client:
        yield client
    # Limpeza após testes
    conn = sqlite3.connect('fintech.db')
    c = conn.cursor()
    c.execute("DELETE FROM users")
    c.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()

def test_login_senha_incorreta(client):
    """Teste de login com senha incorreta -> O sistema deve exibir mensagem de erro"""
    # Cria usuário válido
    client.post('/register', data=dict(email="teste@qa.com", password="123"))
    # Tenta logar com senha errada
    response = client.post('/login', data=dict(email="teste@qa.com", password="errada"))
    assert response.status_code == 401
    assert b"Erro: Credenciais incorretas" in response.data

def test_cadastro_email_invalido(client):
    """Cadastro de usuário com e-mail inválido -> O sistema deve rejeitar o cadastro"""
    response = client.post('/register', data=dict(email="emailinvalido.com", password="123"))
    assert response.status_code == 400
    assert b"Erro: E-mail inv\xc3\xa1lido" in response.data # "inválido" encodado

def test_insercao_despesa_valor_negativo(client):
    """Inserção de despesa com valor negativo -> O sistema deve bloquear a operação"""
    client.post('/register', data=dict(email="user@qa.com", password="123"))
    client.post('/login', data=dict(email="user@qa.com", password="123"))
    
    response = client.post('/transaction', data=dict(type="despesa", amount="-50.00", description="Mercado"))
    assert response.status_code == 400
    assert b"Erro: O valor n\xc3\xa3o pode ser negativo" in response.data

def test_registro_receita_valor_valido(client):
    """Registro de receita com valor válido -> O sistema deve salvar corretamente"""
    client.post('/register', data=dict(email="user@qa.com", password="123"))
    client.post('/login', data=dict(email="user@qa.com", password="123"))
    
    response = client.post('/transaction', data=dict(type="receita", amount="1500.00", description="Salario"))
    assert response.status_code == 302 # Redirect pro dashboard significa sucesso

def test_exclusao_transacao_existente(client):
    """Exclusão de transação existente -> O sistema deve remover o registro com sucesso"""
    client.post('/register', data=dict(email="user@qa.com", password="123"))
    client.post('/login', data=dict(email="user@qa.com", password="123"))
    
    # Adiciona transação
    client.post('/transaction', data=dict(type="receita", amount="100.00", description="Venda"))
    
    # Exclui a transação de ID 1
    response = client.post('/transaction/delete/1')
    assert response.status_code == 302 # Redirect com sucesso
    
    # Verifica dashboard se está vazio
    dashboard = client.get('/dashboard')
    assert b"VENDA" not in dashboard.data.upper()

def test_consulta_saldo_multiplas_transacoes(client):
    """Consulta de saldo após múltiplas transações -> O saldo deve ser calculado corretamente"""
    client.post('/register', data=dict(email="user@qa.com", password="123"))
    client.post('/login', data=dict(email="user@qa.com", password="123"))
    
    # +2000 Receita, -500 Despesa, -100 Despesa = 1400 Saldo
    client.post('/transaction', data=dict(type="receita", amount="2000.00", description="Salario"))
    client.post('/transaction', data=dict(type="despesa", amount="500.00", description="Aluguel"))
    client.post('/transaction', data=dict(type="despesa", amount="100.00", description="Luz"))
    
    response = client.get('/dashboard')
    assert b"R$ 1400.0" in response.data