from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_restful import Api, Resource
import random
from sqlalchemy.exc import SQLAlchemyError
from models import setup_db, Question, Category

QUESTIONS_PER_PAGE = 10

db = SQLAlchemy()

def paginate_questions(request, query):
    page_number = request.args.get("page", 1, type=int)
    paginated_questions = query.paginate(page=page_number, per_page=QUESTIONS_PER_PAGE)
    formatted_questions = [question.format() for question in paginated_questions.items]
    return formatted_questions, paginated_questions.total

def create_app(test_config=None):
    app = Flask(__name__)
    api = Api(app)
    if test_config is None:
        setup_db(app)
    else:
        database_path = test_config.get('SQLALCHEMY_DATABASE_URI')
        setup_db(app, database_path=database_path)

    CORS(app, resources={'/': {'origins': '*'}})

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, true')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS')
        return response

    class CategoryResource(Resource):
        def get(self):
            try:
                all_categories = Category.query.order_by(Category.id).all()
                categories_dict = {category.id: category.type for category in all_categories}

                if len(categories_dict) == 0:
                    abort(404)

                return jsonify({
                    'categories': categories_dict,
                    'success': True
                })
            except SQLAlchemyError as e:
                print(e)
                abort(500)

    class QuestionListResource(Resource):
        def get(self):
            try:
                query = Question.query.order_by(Question.id)
                paginated_questions, total_questions = paginate_questions(request, query)

                if len(paginated_questions) == 0:
                    abort(404)
                
                all_categories = Category.query.all()
                categories_dict = {category.id: category.type for category in all_categories}

                return jsonify({
                    'success': True,
                    'total_questions': total_questions,
                    'categories': categories_dict,
                    'questions': paginated_questions
                })
            except SQLAlchemyError as e:
                print(e)
                abort(500)

        def post(self):
            try:
                request_body = request.get_json()
                question_text = request_body.get('question', None)
                answer_text = request_body.get('answer', None)
                difficulty_level = request_body.get('difficulty', None)
                category_id = request_body.get('category',  None)

                # check empty before insert DB
                if not question_text or not answer_text:
                    abort(400, description="The question and answer fields cannot be empty.")
                
                new_question = Question(question=question_text, answer=answer_text, difficulty=difficulty_level, category=category_id)
                new_question.insert()

                query = Question.query.order_by(Question.id)
                paginated_questions, total_questions = paginate_questions(request, query)

                return jsonify({
                    'success': True,
                    'question_created': new_question.question,
                    'created': new_question.id,
                    'questions': paginated_questions,
                    'total_questions': total_questions
                })
            except SQLAlchemyError as e:
                print(e)
                abort(422)
            except ValueError as e:
                print(e)
                abort(400, description="Invalid data provided.")
            except Exception as e:
                print(e)
                abort(500)

    class QuestionSearchResource(Resource):
        def post(self):
            try:
                request_body = request.get_json()
                search_term = request_body.get('searchTerm', None)
                
                if not search_term:
                    abort(400, description="Search term cannot be empty.")

                matched_questions = Question.query.filter(Question.question.ilike(f"%{search_term}%")).order_by(Question.id)
                paginated_questions, total_questions = paginate_questions(request, matched_questions)
                
                return jsonify({
                    'success': True,
                    'questions': paginated_questions,
                    'total_questions': total_questions
                })
            except SQLAlchemyError as e:
                print(e)
                abort(422)
            except Exception as e:
                print(e)
                abort(500)

    class QuestionResource(Resource):
        def delete(self, question_id):
            try:
                question_to_delete = Question.query.filter_by(id=question_id).one_or_none()
                if question_to_delete is None:
                    abort(404)

                question_to_delete.delete()
                total_questions = Question.query.count()

                return jsonify({
                    'deleted': question_id,
                    'success': True,
                    'total_questions': total_questions
                })
            except SQLAlchemyError as e:
                print(e)
                abort(500)

    class CategoryQuestionsResource(Resource):
        def get(self, category_id):
            try:
                category = Category.query.filter_by(id=category_id).one_or_none()
                if category is None:
                    abort(404)

                query = Question.query.filter_by(category=category.id).order_by(Question.id)
                paginated_questions, total_questions = paginate_questions(request, query)

                return jsonify({
                    'success': True,
                    'total_questions': total_questions,
                    'current_category': category.type,
                    'questions': paginated_questions
                })
            except SQLAlchemyError as e:
                print(e)
                abort(400)

    def get_next_question(previous_questions, quiz_category):
        """Get the next question for the quiz."""
        category_id = quiz_category['id'] if quiz_category else 0

        if category_id != 0:
            available_questions = Question.query.filter_by(category=category_id).filter(
                Question.id.notin_(previous_questions)).all()
        else:
            available_questions = Question.query.filter(
                Question.id.notin_(previous_questions)).all()

        if available_questions:
            return random.choice(available_questions).format()
        else:
            return None

    class QuizResource(Resource):
        def post(self):
            try:
                request_body = request.get_json()
                previous_questions = request_body.get('previous_questions', [])
                quiz_category = request_body.get('quiz_category', None)

                next_question = get_next_question(previous_questions, quiz_category)

                return jsonify({
                    'question': next_question,
                    'success': True,
                })
            except SQLAlchemyError as e:
                print(e)
                abort(422)
            except Exception as e:
                print(e)
                abort(500)

    api.add_resource(CategoryResource, '/categories')
    api.add_resource(QuestionListResource, '/questions')
    api.add_resource(QuestionSearchResource, '/questions/search')
    api.add_resource(QuestionResource, '/questions/<int:question_id>', methods=['DELETE'])
    api.add_resource(CategoryQuestionsResource, '/categories/<int:category_id>/questions')
    api.add_resource(QuizResource, '/play')

    @app.errorhandler(400)
    def bad_request_error(error):
        return jsonify({
            "success": False,
            "error": 400,
            "message": error.description if hasattr(error, 'description') else "bad request"
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "error": 404,
            "message": "resource not found"
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'success': False,
            'error': 405,
            'message': 'method not allowed'
        }), 405

    @app.errorhandler(422)
    def unprocessable(error):
        return jsonify({
            "success": False,
            "error": 422,
            "message": "unprocessable"
        }), 422

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            "success": False,
            "error": 500,
            "message": "internal server error"
        }), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
