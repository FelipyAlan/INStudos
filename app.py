from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usuarios.db'
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
db = SQLAlchemy(app)

# Modelo de Usuário
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    idade = db.Column(db.Integer, nullable=False)
    curso = db.Column(db.String(100), nullable=False)
    senha = db.Column(db.String(100), nullable=False)
    postagens = db.relationship('Postagem', backref='autor', lazy=True)
    preferencias = db.relationship('PreferenciaEstudo', back_populates='usuario', cascade="all, delete-orphan")

# Modelo de Postagem
class Postagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

# Modelo de Preferência de Estudo
class PreferenciaEstudo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    materia = db.Column(db.String(100), nullable=False)
    usuario = db.relationship('Usuario', back_populates='preferencias')

# Modelo de Mensagem
class Mensagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    remetente_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    data_envio = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    remetente = db.relationship('Usuario', foreign_keys=[remetente_id])
    destinatario = db.relationship('Usuario', foreign_keys=[destinatario_id])


# Rota para a página inicial (Login)
@app.route('/')
def index():
    return render_template('index.html')

# Rota para cadastro
@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome = request.form['nome']
        idade = request.form['idade']
        curso = request.form['curso']
        senha = request.form['senha']

        usuario_existente = Usuario.query.filter_by(nome=nome).first()
        if usuario_existente:
            flash('Usuário já cadastrado. Tente outro nome.', 'warning')
            return redirect(url_for('cadastrar'))

        novo_usuario = Usuario(nome=nome, idade=idade, curso=curso, senha=senha)
        db.session.add(novo_usuario)
        db.session.commit()
        flash('Cadastro realizado com sucesso! Faça login.', 'success')
        return redirect(url_for('index'))

    return render_template('cadastrar.html')

# Rota para login
@app.route('/login', methods=['POST'])
def login():
    nome = request.form['nome']
    senha = request.form['senha']

    usuario = Usuario.query.filter_by(nome=nome, senha=senha).first()

    if usuario:
        session['usuario_id'] = usuario.id
        flash('Login bem-sucedido!', 'success')
        return redirect(url_for('perfil', usuario_id=usuario.id))
    else:
        flash('Nome ou senha incorretos. Tente novamente.', 'danger')
        return redirect(url_for('index'))

# Rota para o perfil do usuário (autenticado)
@app.route('/perfil/<int:usuario_id>')
def perfil(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    return render_template('perfil.html', usuario=usuario)

# Rota para visualizar o perfil de outro usuário
@app.route('/perfil_usuario/<int:usuario_id>')
def perfil_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    return render_template('perfil_usuario.html', usuario=usuario)

# Rota para criar uma nova postagem
@app.route('/postar', methods=['POST'])
def postar():
    titulo = request.form['titulo']
    conteudo = request.form['conteudo']
    usuario_id = session['usuario_id']

    nova_postagem = Postagem(titulo=titulo, conteudo=conteudo, usuario_id=usuario_id)
    db.session.add(nova_postagem)
    db.session.commit()
    flash('Postagem criada com sucesso!', 'success')
    return redirect(url_for('perfil', usuario_id=usuario_id))

# Rota para configurar preferências de estudo
@app.route('/preferencias', methods=['GET', 'POST'])
def preferencias():
    if request.method == 'POST':
        usuario_id = session['usuario_id']
        materia = request.form['materia']

        nova_preferencia = PreferenciaEstudo(usuario_id=usuario_id, materia=materia)
        db.session.add(nova_preferencia)
        db.session.commit()
        flash('Preferência adicionada com sucesso!', 'success')
        return redirect(url_for('preferencias'))

    usuario = Usuario.query.get(session['usuario_id'])
    return render_template('preferencias.html', usuario=usuario)

# Rota para encontrar matches
@app.route('/matches', methods=['GET', 'POST'])
def matches():
    usuario = Usuario.query.get(session['usuario_id'])
    preferencias_usuario = [p.materia for p in usuario.preferencias]

    if request.method == 'POST':
        filtro_curso = request.form['filtro_curso']
        matches = Usuario.query.filter(
            Usuario.id != usuario.id,
            Usuario.preferencias.any(PreferenciaEstudo.materia.in_(preferencias_usuario)),
            Usuario.curso == filtro_curso
        ).all()
    else:
        matches = Usuario.query.filter(
            Usuario.id != usuario.id,
            Usuario.preferencias.any(PreferenciaEstudo.materia.in_(preferencias_usuario))
        ).all()

    cursos_disponiveis = Usuario.query.with_entities(Usuario.curso).distinct().all()

    return render_template('matches.html', matches=matches, cursos=cursos_disponiveis)

# Rota para ver e enviar mensagens
@app.route('/mensagens/<int:usuario_id>', methods=['GET', 'POST'])
def mensagens(usuario_id):
    usuario_destinatario = Usuario.query.get_or_404(usuario_id)

    if request.method == 'POST':
        conteudo = request.form['conteudo']
        nova_mensagem = Mensagem(remetente_id=session['usuario_id'], destinatario_id=usuario_destinatario.id, conteudo=conteudo)
        db.session.add(nova_mensagem)
        db.session.commit()
        flash('Mensagem enviada com sucesso!', 'success')
        return redirect(url_for('mensagens', usuario_id=usuario_destinatario.id))

    mensagens = Mensagem.query.filter(
        ((Mensagem.remetente_id == session['usuario_id']) & (Mensagem.destinatario_id == usuario_destinatario.id)) |
        ((Mensagem.remetente_id == usuario_destinatario.id) & (Mensagem.destinatario_id == session['usuario_id']))
    ).order_by(Mensagem.data_envio).all()

    return render_template('mensagens.html', usuario_destinatario=usuario_destinatario, mensagens=mensagens)

# Inicializa o banco de dados
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Isso cria todas as tabelas, incluindo Mensagem
    app.run(debug=True)










