from flask import Flask, request
from flask import jsonify
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_marshmallow import Marshmallow  
from dateutil.parser import parse
from datetime import datetime
from flask_jwt import JWT, jwt_required, current_identity
from werkzeug.security import safe_str_cmp

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SECRET_KEY'] = 'super-secret'

db = SQLAlchemy(app)

ma = Marshmallow(app)

api = Api(app)

class Evento(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    creador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    nombre = db.Column( db.String(255) )
    categoria = db.Column( db.String(255) )
    lugar = db.Column( db.String(255) )
    direccion = db.Column( db.String(255) )
    fechaInicio = db.Column( db.Date)
    fechaFin = db.Column( db.Date)
    tipo = db.Column( db.String(255) )

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    login = db.Column( db.String(255) )
    contrasena = db.Column( db.String(255) )
    eventos = relationship('Evento',backref='creador')
    token = db.Column(db.String(255))


class Evento_Shema(ma.Schema):
    class Meta:
        fields = ("id", "creador_id", "nombre", "categoria", "lugar", "direccion", "fechaInicio", "fechaFin", "tipo")

class Usuario_Shema(ma.Schema):
    class Meta:
        fields = ("id", "login", "contrasena","token") 

post_evento_schema = Evento_Shema()
posts_evento_schema = Evento_Shema(many = True)

post_usuario_schema = Usuario_Shema()
posts_usuario_schema = Usuario_Shema(many = True)

def authenticate(username, password):
    user = Usuario.query.filter_by(login = username, contrasena=password).first()        
    return user

def identity(payload):
    print(payload['identity'])
    return Usuario.query.filter_by( id = payload['identity']).scalar()

jwt = JWT(app, authenticate, identity)
class RecursoListarUsuarios(Resource):
    def get(self):
        usuarios = Usuario.query.all()
        return posts_usuario_schema.dump(usuarios)

    def post(self):
            usuarioExistente = Usuario.query.filter_by(login = request.json['login'], contrasena=request.json['contrasena']).first()        
            if usuarioExistente :
                return post_usuario_schema.dump(usuarioExistente)
            nuevo_usuario = Usuario(
                login = request.json['login'],
                contrasena=request.json['contrasena']
            )
            db.session.add(nuevo_usuario)
            db.session.commit()
            return post_usuario_schema.dump(nuevo_usuario)

class RecursoUnUsuario(Resource):
    def get(self, id_usuario):
        usuario = Usuario.query.get_or_404(id_usuario)
        return post_usuario_schema.dump(usuario)
    def put(self, id_usuario):
        usuario = Usuario.query.get_or_404(id_usuario)
        if 'login' in request.json:
            usuario.login = request.json['login']
        if 'contrasena' in request.json:
            usuario.contrasena = request.json['contrasena']
        if 'token' in request.json:
            usuario.token = request.json['token']
        db.session.commit()
        return post_usuario_schema.dump(usuario)
    def delete(self, id_usuario):
        usuario = Usuario.query.get_or_404(id_usuario)
        db.session.delete(usuario)
        db.session.commit()
        return '', 204

class RecursoUnUsuarioLoginPassword(Resource):
    def get(self, login,password):
        usuario = Usuario.query.filter_by(login = login, contrasena=password).first()
        retorno = result = post_evento_schema.dump(usuario)
        if len(result)==0:
            retorno = "No se encontró el usuario"
        return retorno 
class RecursoListarEventosUsuario(Resource):
    def orden(a,b):
        a_time = date.fromisoformat(a['fechaInicio'])
        b_time =  date.fromisoformat(b['fechaInicio'])
        return 1 if a > b  else -1 if a < b else 0


    @jwt_required()
    def get(self, id_usuario):
        eventos = Evento.query.filter(Evento.creador_id == id_usuario)
        lista=posts_evento_schema.dump(eventos)
        ordenados=sorted(lista, key=lambda x:x['fechaInicio'])
        return ordenados

    @jwt_required()
    def post(self,id_usuario):
        if 'nombre' in request.json:
            if len(request.json['nombre'])==0:
                return {"error": "No esta el nuevo nombre del evento"},412

        if 'categoria' in request.json:
            if request.json['categoria'] in('Conferencia','Seminario','Congreso','Curso'):
                pass
            else:
                return {"error": "La categoria del evento no es valida"},412

        if 'lugar' in request.json:
            if len(request.json['lugar'])==0:
                 return {"error": "No esta el nuevo lugar del evento"},412

        if 'direccion' in request.json:
            if len(request.json['direccion'])==0:
                 return {"error": "No esta la nueva direccion del evento"},412
        
        if 'fechaInicio' in request.json and 'fechaFin' in request.json:
            if parse(request.json['fechaInicio']).date() <= parse(request.json['fechaInicio']).date():
                pass
            else:
                return {"error": "La fecha inicial es mayor a la final"},412
        if 'tipo' in request.json:
            if request.json['tipo'] in('Presencial','Virtual'):
                pass
            else:
                return {"error": "El tipo de evento no es valido"},412
            nuevo_evento = Evento(
                creador_id = id_usuario,
                nombre=request.json['nombre'],
                categoria=request.json['categoria'],
                lugar=request.json['lugar'],
                direccion=request.json['direccion'],
                fechaInicio = parse(request.json['fechaInicio']).date(),
                fechaFin = parse(request.json['fechaFin']).date(),
                tipo=request.json['tipo']
            )
            db.session.add(nuevo_evento)
            db.session.commit()
            result= post_evento_schema.dump(nuevo_evento)
            return jsonify(result) 

class RecursoUnEventoDeUsuario(Resource):
    @jwt_required()
    def get(self,id_usuario,id_evento):
        evento = Evento.query.filter_by(creador_id = id_usuario, id=id_evento).first()
        retorno = result = post_evento_schema.dump(evento)
        if len(result)==0:
            retorno = "No se encontró el evento"
        return retorno
        #Si len( post_evento_schema.dump(evento)) == 0 es que no se encuentra el elemento

    @jwt_required()
    def put(self,id_usuario,id_evento):
        evento = Evento.query.filter_by(creador_id = id_usuario, id=id_evento).first()    
        if 'nombre' in request.json:
            if len(request.json['nombre'])==0:
                 return {"error": "No esta el nuevo nombre del evento"},412
            evento.nombre = request.json['nombre']

        if 'categoria' in request.json:
            if request.json['categoria'] in('Conferencia','Seminario','Congreso','Curso'):
                evento.categoria = request.json['categoria']
            else:
                return {"error": "La categoria del evento no es valida"},412

        if 'lugar' in request.json:
            if len(request.json['lugar'])==0:
                 return {"error": "No esta el nuevo lugar del evento"},412
            evento.lugar = request.json['lugar']

        if 'direccion' in request.json:
            if len(request.json['direccion'])==0:
                 return {"error": "No esta la nueva direccion del evento"},412
            evento.direccion = request.json['direccion']
        
        if 'fechaInicio' in request.json and 'fechaFin' in request.json:
            if parse(request.json['fechaInicio']).date() <= parse(request.json['fechaInicio']).date():
                evento.fechaInicio =parse(request.json['fechaInicio']).date()
                evento.fechaFin = parse(request.json['fechaFin']).date()
            else:
                return {"error": "La fecha inicial es mayor a la final"},412
        if 'tipo' in request.json:
            if request.json['tipo'] in('Presencial','Virtual'):
                evento.tipo = request.json['tipo']
            else:
                return {"error": "El tipo de evento no es valido"},412
        db.session.commit()
        return post_evento_schema.dump(evento)

    def delete(self,id_usuario,id_evento):
        evento = Evento.query.filter_by(creador_id = id_usuario, id=id_evento).first()        
        db.session.delete(evento)
        db.session.commit()
        return "Elimidado"

api.add_resource(RecursoListarUsuarios, '/usuarios')
api.add_resource(RecursoUnUsuario,'/usuarios/<int:id_usuario>')

api.add_resource(RecursoListarEventosUsuario,'/usuarios/<int:id_usuario>/eventos')
api.add_resource(RecursoUnEventoDeUsuario,'/usuarios/<int:id_usuario>/eventos/<int:id_evento>')
api.add_resource(RecursoUnUsuarioLoginPassword,'/usuarios/<login>/<password>')

if __name__ == '__main__':
    app.run(debug=True)

