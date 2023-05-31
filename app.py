from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
from datetime import datetime
import csv
from io import StringIO
from functools import wraps
import requests

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'asdasdasdas'


# Classe Ticket para representar um ticket de suporte
class Ticket:
    def __init__(self, numero, cliente, telefone_cliente, assunto, descricao, status='Fechado'):
        self.numero = numero
        self.cliente = cliente
        self.telefone_cliente = telefone_cliente
        self.assunto = assunto
        self.descricao = descricao
        self.status = status
        self.data_inicial = None
        self.data_final = None
        self.mensagens = []

    def adicionar_mensagem(self, autor, texto, tipo_autor):
        mensagem = Mensagem(autor, texto, tipo_autor)
        self.mensagens.append(mensagem)

    def adicionar_mensagem_helpdesk():
        data = request.json  # Usar request.json para.



# Classe Mensagem para representar uma mensagem em um ticket
class Mensagem:
    def __init__(self, autor, texto, tipo_autor):
        self.autor = autor
        self.texto = texto
        self.tipo_autor = tipo_autor


# Classe Cliente para representar um cliente
class Cliente:
    def __init__(self, id_cliente, nome):
        self.id = id_cliente
        self.nome = nome


# Classe Atendente para representar um atendente
class Atendente:
    def __init__(self, nome, senha):
        self.nome = nome
        self.senha = senha


# Classe Helpdesk para gerenciar os tickets, clientes e atendentes
class Helpdesk:
    def __init__(self):
        self.tickets = []
        self.tickets_fechados = []  # Lista de tickets fechados
        self.numero_ticket_counter = 1
        self.clientes = {}
        self.atendentes = {}   # Dicionário de atendentes (nome: objeto Atendente)

    def adicionar_cliente(self, nome):
        id_cliente = len(self.clientes) + 1
        cliente = Cliente(id_cliente, nome)
        self.clientes[id_cliente] = cliente
        return cliente

    def adicionar_atendente(self, nome, senha):
        atendente = Atendente(nome, senha)
        self.atendentes[nome] = atendente
        return atendente

    def autenticar_atendente(self, nome, senha):
        atendente = self.atendentes.get(nome)
        if atendente and atendente.senha == senha:
            return True
        else:
            return False

    def abrir_ticket(self, id_cliente, telefone_cliente, assunto, descricao, status='Fechado'):
        numero_ticket = self.numero_ticket_counter
        ticket = Ticket(numero_ticket, self.clientes[id_cliente].nome, telefone_cliente, assunto, descricao, status)
        ticket.data_inicial = datetime.now()  # Registra a data inicial
        self.numero_ticket_counter += 1
        self.tickets.append(ticket)
        return ticket

    def fechar_ticket(self, numero_ticket):
        ticket = next((t for t in self.tickets if t.numero == numero_ticket), None)
        if ticket:
            ticket.status = 'Fechado'
            ticket.data_final = datetime.now()  # Registra a data final
            tempo_ocorrido = ticket.data_final - ticket.data_inicial
            ticket.tempo_ocorrido = tempo_ocorrido  # Calcula o tempo decorrido

            self.tickets.remove(ticket)  # Remove o ticket da lista de tickets
            self.tickets_fechados.append(ticket)  # Adiciona o ticket à lista de tickets fechados
        else:
            raise ValueError("Ticket não encontrado")
        
    def adicionar_mensagem_helpdesk(self, numero_cliente, mensagem):
        ticket = next((t for t in self.tickets if t.telefone_cliente == numero_cliente), None)
        if ticket:
            ticket.adicionar_mensagem(ticket.cliente, mensagem, 'Atendente')
            return {'success': True}  # Adicione esta linha
        else:
            return {'success': False, 'error': 'Ticket não encontrado'}


    def obter_tickets(self):
        return self.tickets
    
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'autenticado' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


helpdesk = Helpdesk()
helpdesk.adicionar_atendente("admin", "senha")
helpdesk.adicionar_atendente("felipe", "felipe")


# Exemplo de adição de um atendente
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'autenticado' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        nome_atendente = request.form['atendente']
        senha = request.form['senha']

        if helpdesk.autenticar_atendente(nome_atendente, senha):
            session['autenticado'] = True
            session['nome_atendente'] = nome_atendente  # Armazena o nome do atendente na sessão
            return redirect(url_for('home'))
        else:
            return "Autenticação falhou. Verifique seu nome de usuário e senha."
    else:
        return render_template('login.html')


@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if 'autenticado' not in session:
        return redirect(url_for('login'))

    lista_tickets = helpdesk.obter_tickets()  # Obtém a lista de tickets do helpdesk
    tickets_abertos = [ticket for ticket in lista_tickets if ticket.status != 'Fechado']
    tickets_fechados = [ticket for ticket in lista_tickets if ticket.status == 'Fechado']

    return render_template('home.html', tickets_abertos=tickets_abertos, tickets_fechados=tickets_fechados)



@app.route('/criar_ticket', methods=['GET', 'POST'])
#@login_required
def criar_ticket():
    if request.method == 'POST':
        nome_cliente = request.form.get('cliente')
        if nome_cliente:
            telefone_cliente = request.form['telefone_cliente']
            assunto = request.form['assunto']
            descricao = request.form['descricao']
            status = request.form['status']
            origem = request.form['origem']

            cliente_existente = next(
                (cliente for cliente in helpdesk.clientes.values() if cliente.nome == nome_cliente), None)
            if not cliente_existente:
                novo_cliente = helpdesk.adicionar_cliente(nome_cliente)
                id_cliente = novo_cliente.id
            else:
                id_cliente = cliente_existente.id

            ticket = helpdesk.abrir_ticket(id_cliente, telefone_cliente, assunto, descricao, status)
            ticket.origem = origem

            return redirect(url_for('criar_ticket'))

    return render_template('criar_ticket.html', tickets=helpdesk.obter_tickets(), clientes=helpdesk.clientes.values(),
                           helpdesk=helpdesk)



@app.route('/fechar_ticket/<int:numero_ticket>', methods=['POST'])
@login_required
def fechar_ticket(numero_ticket):
    try:
        helpdesk.fechar_ticket(numero_ticket)
        return redirect(url_for('exibir_tickets_fechados'))  # Alteração: redirecionar para 'exibir_tickets_fechados'
    except ValueError as e:
        return str(e)

    


    
@app.route('/tickets_fechados', methods=['GET', 'POST'])
@login_required
def exibir_tickets_fechados():
    tickets_fechados = helpdesk.tickets_fechados  # Alteração: use helpdesk.tickets_fechados
    return render_template('tickets_fechados.html', tickets_fechados=tickets_fechados)





@app.route('/adicionar_mensagem/<int:numero_ticket>', methods=['POST'])
@login_required
def adicionar_mensagem(numero_ticket):
    texto = request.form['mensagem']
    ticket = next((t for t in helpdesk.tickets if t.numero == numero_ticket), None)
    if ticket:
        if 'autenticado' in session:
            autor = session['nome_atendente']  # Obtém o nome do atendente logado da sessão
            tipo_autor = 'Atendente'
        else:
            autor = request.form['autor']
            tipo_autor = 'Cliente'

        if ticket.status == 'Fechado':
            return "Este ticket está fechado. Não é possível adicionar mensagens."
        
        if 'autenticado' in session:
            autor = session['nome_atendente']
            tipo_autor = 'Atendente'
        else:
            autor = request.form['autor']
            tipo_autor = 'Cliente'


        ticket.adicionar_mensagem(autor, texto, tipo_autor)

        # Puxa o número do cliente do ticket e coloca na variável numero_cliente
        numero_cliente = ticket.telefone_cliente

        # Realize a solicitação HTTP para enviar a mensagem ao Venom Bot
        url = 'http://127.0.0.1:3000/receber_mensagem_helpdesk'
        payload = {
            'numero_cliente': numero_cliente,
            'mensagem': "*"+ autor +"*\n\n\n" + texto,
        }
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            return redirect(url_for('exibir_ticket', numero_ticket=numero_ticket))
        else:
            return "Erro ao adicionar mensagem"
    else:
        return "Ticket não encontrado"
    

@app.route('/adicionar_mensagem_helpdesk', methods=['POST'])
def adicionar_mensagem_helpdesk():
    data = request.get_json()
    numero_cliente = data['numero_cliente']
    mensagem = data['mensagem']

    response = helpdesk.adicionar_mensagem_helpdesk(numero_cliente, mensagem)
    return jsonify(response)


@app.route('/ticket/<int:numero_ticket>')
@login_required
def exibir_ticket(numero_ticket):
    ticket = next((t for t in helpdesk.tickets if t.numero == numero_ticket), None)
    if ticket:
        return render_template('ticket.html', ticket=ticket, tickets=helpdesk.obter_tickets(), clientes=helpdesk.clientes.values(),
                           helpdesk=helpdesk)
    else:
        return "Ticket não encontrado"
    



@app.route('/relatorio', methods=['POST'])
@login_required
def gerar_relatorio():
    relatorio = []

    if 'quantos_tickets_atendidos' in request.form:
        quantidade_tickets = len(helpdesk.tickets_fechados)  # Alteração: use helpdesk.tickets_fechados
        relatorio.append(f"Quantidade de Tickets Atendidos: {quantidade_tickets}")

    if 'clientes_com_mais_chamados' in request.form:
        clientes_chamados = {}
        for ticket in helpdesk.tickets_fechados:  # Alteração: use helpdesk.tickets_fechados
            cliente = ticket.cliente
            if cliente in clientes_chamados:
                clientes_chamados[cliente] += 1
            else:
                clientes_chamados[cliente] = 1

        clientes_chamados_ordenados = sorted(clientes_chamados.items(), key=lambda x: x[1], reverse=True)
        relatorio.append("Clientes com Mais Chamados:")
        for cliente, quantidade in clientes_chamados_ordenados:
            relatorio.append(f"{cliente}: {quantidade} chamado(s)")

    if 'maiores_tempos_corridos' in request.form:
        tickets_resolvidos = sorted(helpdesk.tickets_fechados, key=lambda x: x.tempo_ocorrido, reverse=True)  # Alteração: use helpdesk.tickets_fechados
        relatorio.append("Maiores Tempos Decorridos de Chamados:")
        for ticket in tickets_resolvidos:
            relatorio.append(f"Numero do Ticket: {ticket.numero}, Tempo Decorrido: {ticket.tempo_ocorrido}")

    if 'chamados_resolvidos' in request.form:
        quantidade_resolvidos = len(helpdesk.tickets_fechados)  # Alteração: use helpdesk.tickets_fechados
        relatorio.append(f"Quantidade de Chamados Resolvidos: {quantidade_resolvidos}")

    if 'chamados_pendentes' in request.form:
        quantidade_pendentes = len(helpdesk.tickets) - len(helpdesk.tickets_fechados)  # Alteração: use helpdesk.tickets e helpdesk.tickets_fechados
        relatorio.append(f"Quantidade de Chamados Pendentes: {quantidade_pendentes}")
 
    if 'mensagens_cliente' in request.form:
        relatorio.append("Mensagens Trocadas por Cliente:")
        for cliente in helpdesk.clientes:
            relatorio.append(f"Cliente: {cliente}")
            mensagens_cliente = []
            for ticket in helpdesk.tickets_fechados:
                if ticket.cliente == cliente:
                    mensagens_cliente.extend(ticket.mensagens)
            for mensagem in mensagens_cliente:
                relatorio.append(mensagem)
            relatorio.append("")  # Adiciona uma linha vazia para separar os clientes


    # Gerar o arquivo CSV com o relatório
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    for linha in relatorio:
        writer.writerow([linha])

    # Prepara a resposta com o arquivo CSV
    response = make_response(csv_buffer.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=relatorio.csv"
    response.headers["Content-type"] = "text/csv"

    return response




@app.route('/atualizar_mensagens/<int:numero_ticket>', methods=['GET'])
@login_required
def atualizar_mensagens(numero_ticket):
    ticket = next((t for t in helpdesk.tickets if t.numero == numero_ticket), None)
    if ticket:
        return render_template('mensagens.html', ticket=ticket)
    else:
        return "Ticket não encontrado"


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('autenticado', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
