import sqlite3

# Conecta ao banco de dados
conn = sqlite3.connect('fintech.db')
c = conn.cursor()

# Executa a atualização
c.execute("UPDATE users SET is_admin = 1 WHERE email = 'rodrigo@admin.com'")

# O SEGREDINHO AQUI: Salva as alterações de verdade no arquivo
conn.commit()

# Verifica se deu certo
if c.rowcount > 0:
    print("Sucesso! O usuário rodrigo@admin.com agora é Admin.")
else:
    print("Erro: Usuário não encontrado. Verifique se o e-mail está correto.")

conn.close()