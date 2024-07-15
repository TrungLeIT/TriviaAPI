import os
import json
import pytest
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

from flaskr import create_app
from models import setup_db, Question, Category

# Load environment variables from .env file
load_dotenv()

# Retrieve database connection information from environment variables
database_name = os.getenv("DATABASE_NAME")
database_user = os.getenv("DATABASE_USER")
database_password = os.getenv("DATABASE_PASSWORD")
database_host = os.getenv("DATABASE_HOST")
database_port = os.getenv("DATABASE_PORT")

database_path = f"postgresql://{database_user}:{database_password}@{database_host}:{database_port}/{database_name}"

@pytest.fixture(scope='module')
def test_client():
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = database_path
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with flask_app.test_client() as testing_client:
        with flask_app.app_context():
            setup_db(flask_app)
            db = SQLAlchemy()
            db.init_app(flask_app)
            db.create_all()
        yield testing_client

@pytest.fixture(scope='module')
def new_question():
    return {
        'question': 'new question',
        'answer': 'new answer',
        'difficulty': 1,
        'category': 1
    }

def test_get_all_categories(test_client):
    response = test_client.get('/categories')
    response_data = json.loads(response.data)

    assert response.status_code == 200
    assert response_data['success'] is True

def test_get_questions(test_client):
    response = test_client.get('/questions')
    response_data = json.loads(response.data)

    assert response.status_code == 200
    assert response_data['success'] is True

def test_get_questions_404(test_client):
    response = test_client.get('/questions?page=2000')
    response_data = json.loads(response.data)

    assert response.status_code == 404
    assert response_data['success'] is False

def test_delete_question(test_client):
    response = test_client.delete('/questions/2')
    response_data = json.loads(response.data)

    assert response.status_code == 200
    assert response_data['success'] is True
    assert response_data['deleted'] == 2

def test_delete_question_404(test_client):
    response = test_client.delete('/questions/5000')
    response_data = json.loads(response.data)

    assert response.status_code == 404

def test_create_question(test_client, new_question):
    response = test_client.post('/questions', json=new_question)
    response_data = json.loads(response.data)

    assert response.status_code == 200
    assert response_data['success'] is True

def test_405_question_creation_not_allowed(test_client, new_question):
    response = test_client.post('/questions/45', json=new_question)
    response_data = json.loads(response.data)

    assert response.status_code == 405
    assert response_data['success'] is False
    assert response_data['message'] == 'method not allowed'

def test_search(test_client):
    response = test_client.post('/questions', json={'searchTerm': 'invented'})
    response_data = json.loads(response.data)

    assert response.status_code == 200
    assert response_data['success'] is True

def test_search_without_results(test_client):
    response = test_client.post('/questions', json={'searchTerm':'asdf'})
    response_data = json.loads(response.data)

    assert response_data['total_questions'] == 0
    assert response_data['success'] is True

def test_get_questions_by_category(test_client):
    response = test_client.get('/categories/1/questions')
    response_data = json.loads(response.data)

    assert response.status_code == 200
    assert response_data['current_category'] == 'Science'
    assert response_data['success'] is True

def test_get_404_questions_by_category(test_client):
    response = test_client.get('/categories/1000/questions')
    response_data = json.loads(response.data)

    assert response.status_code == 404
    assert response_data['message'] == 'resource not found'
    assert response_data['success'] is False

def test_quiz(test_client):
    quiz_round = {'previous_questions': [], 'quiz_category': {'type': 'Geography', 'id': 14}}
    response = test_client.post('/play', json=quiz_round)
    response_data = json.loads(response.data)

    assert response.status_code == 200
    assert response_data['success'] is True

def test_422_quiz(test_client):
    response = test_client.post('/play', json={})
    response_data = json.loads(response.data)

    assert response.status_code == 422
    assert response_data['success'] is False
    assert response_data['message'] == 'unprocessable'
