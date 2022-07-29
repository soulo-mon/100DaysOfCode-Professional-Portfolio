# Web Development
from flask import Flask, render_template, request, redirect, url_for, flash
# Login Manager
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.exceptions import abort
from werkzeug.security import generate_password_hash, check_password_hash
# Forms
from forms import LoginForm, RegisterForm, ProductForm, CartForm, TransactionForm, ReviewForm
from wtforms.fields import DateField, EmailField, TelField
# Database
from models import db, User, Product, ProductReview, Order, Transaction, TransactionDetail, Category, ProductCategory
# Utilities
from functools import wraps # Decorators
from datetime import datetime
from dotenv import load_dotenv # Environment variables
from os import getenv # Environment variables
from locale import setlocale, currency, LC_ALL # Currency formatter
import pandas as pd # Initialize Products

# Load Environment Variables
load_dotenv()

# Configure Locale
setlocale(LC_ALL, 'id_ID.utf8')

# Create App
app = Flask(__name__)
app.config['SECRET_KEY'] = getenv('SECRET_KEY')

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)

# Config Database URL
if getenv('DATABASE_URL') == None:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///online-shop.db'
else: 
    app.config['SQLALCHEMY_DATABASE_URI'] = getenv('DATABASE_URL').replace("postgres", "postgresql")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database
db.init_app(app)
# Paste code from init.txt here

# Default loading user function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# // ------------------------------ DECORATORS ------------------------------ //

def admin_only(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.id == 1 :
            return func(*args, **kwargs)
        return abort(403)
    return decorated_function

def member_only(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.id != 1 :
            return func(*args, **kwargs)
        return abort(403)
    return decorated_function

# // ------------------------------ TEMPLATE FILTERS ------------------------------ //

@app.template_filter('format_currency')
def format_currency(price:int):
    '''Format currency'''
    return currency(float(price))

@app.template_filter('format_date')
def format_date(date):
    '''Format Date'''
    return date.strftime('%d/%m/%Y')

@app.template_filter('refactor_categories')
def refactor_categories(categories:list):
    '''Change the categories into a more readable string format'''
    if len(categories) == 0:
        return 'Miscellaneous'
    return ', '.join([pc.category.name.replace('And', ' & ') for pc in categories])

@app.template_filter('get_stars')
def get_stars(rating:int):
    '''Convert Rating into stars'''
    return '★' * rating

@app.template_filter('get_average_rating')
def get_average_rating(reviews):
    '''Get average rating and convert them into stars'''
    if len(reviews) == 0:
        return 'Not Rated'
    return '★' * (sum([review.rating for review in reviews]) // len(reviews))

@app.template_filter('get_number_of_reviews')
def get_number_of_reviews(reviews):
    '''Convert Rating into stars'''
    return len(reviews)

@app.template_filter('get_order_count')
def get_order_count(orders):
    '''Get number of products in total (from Order object)'''
    return sum([order.quantity for order in orders])

@app.template_filter('get_products_count')
def get_products_count(details):
    '''Get Number of products in total (from TransactionDetail object)'''
    return sum([detail.quantity for detail in details])

@app.template_filter('get_current_sum')
def get_current_sum(orders):
    '''Get Temporary Total Cost in Cart (from Order object)'''
    return currency(float(sum([order.product.price * order.quantity for order in orders])))

@app.template_filter('get_price_sum')
def get_price_sum(transactions):
    '''Get Total Cost (from Transaction object)'''
    return currency(float(sum([transaction.price * transaction.quantity for transaction in transactions])))

@app.template_filter('get_total_payment')
def get_total_payment(info):
    '''Get Total Cost + Delivery Cost in currency format (from Transaction Object)'''
    return currency(float(info.delivery_cost+sum([transaction.price * transaction.quantity for transaction in info.details])))

# // ------------------------------ BASIC FUNCTIONALITY ------------------------------ //

@app.route('/')
@app.route('/<int:page>')
def home(page=1):
    products = Product.query.paginate(page,9)
    return render_template('index.html', products = products)

@app.route('/category/<int:id>')
@app.route('/category/<int:id>/<int:page>')
def get_by_category(id:int, page=1):
    products = Product.query.join(ProductCategory).filter_by(category_id=id).paginate(page,9)
    return render_template('index.html', products= products)

@app.route('/search')
@app.route('/search/<int:page>')
def search_product(page=1):
    query = request.args.get('search')
    products = Product.query.filter(Product.name.like(f'%{query}%')).paginate(page,9)
    return render_template('index.html', products= products)

# // ------------------------------ USER AUTHENTICATION ------------------------------ //

@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        find_user = User.query.filter_by(email=request.form.get('email')).first()
        if find_user is None:
            new_user = User(
                name = request.form.get('name'),
                email = request.form.get('email'),
                password = generate_password_hash(
                    request.form.get('password'),
                    method='pbkdf2:sha256',
                    salt_length=13,
                ),
                dob = datetime.strptime(request.form.get('dob'),'%Y-%m-%d'),
            )
            with app.app_context():
                db.session.add(new_user)
                db.session.commit()
        else:
            flash('User already exists, Please login!')
        return redirect(url_for('login'))
    return render_template('auth.html', form=form, purpose='register')

@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        print("Login")
        find_user = User.query.filter_by(email=request.form.get('email')).first()
        if find_user is None:
            flash("User doesn't exist! Please register!")
            return redirect(url_for('register'))
        elif check_password_hash(find_user.password, request.form.get('password')):
            login_user(find_user)
            return redirect(url_for('home'))
        else:
            flash('Wrong email or password!')
    return render_template('auth.html', form=form, purpose='login')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# // ------------------------------ PRODUCT MANAGEMENT (CRUD) ------------------------------ //

@app.route('/products/add', methods=['GET','POST'])
@admin_only
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        find_product = Product.query.filter_by(name=request.form.get('name')).first()
        if find_product is None:
            new_product = Product(
                name = request.form.get('name'),
                description = request.form.get('description'),
                image_url = request.form.get('image_url'),
                price = request.form.get('price'),
                stock = request.form.get('stock'),
            )
            with app.app_context():
                db.session.add(new_product)
                db.session.commit()
                for category in form.categories.data:
                    new_product_category = ProductCategory(
                        product = new_product,
                        category = Category.query.filter_by(name=category).first()
                    )
                db.session.add(new_product_category)
                db.session.commit()
            return redirect(url_for('home'))
    return render_template('product_manager.html', purpose = 'add', form = form)

@app.route('/products/update/<int:id>', methods=['GET', 'POST'])
@admin_only
def update_product(id:int):
    product = Product.query.filter_by(id=id).first()
    form = ProductForm(
        name = product.name,
        description=product.description,
        image_url=product.image_url,
        price = product.price,
        stock = product.stock,
        categories = [category for category in product.categories]
    )
    if form.validate_on_submit():
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.image_url = request.form.get('image_url')
        product.price = request.form.get('price')
        product.stock = request.form.get('stock')
        categories = ProductCategory.query.filter_by(product_id=id)
        with app.app_context():
            for category in categories:
                db.session.delete(category)
                db.session.commit()
            for category in form.categories.data:
                new_product_category = ProductCategory(
                    product = product,
                    category = Category.query.filter_by(name=category).first()
                )
                db.session.add(new_product_category)
                db.session.commit()
        return redirect(url_for('get_product', id=id))
    return render_template('product_manager.html', product=product, purpose = 'update', form = form)

@app.route('/products/<int:id>', methods=['GET', 'POST'])
def get_product(id:int):
    product = Product.query.filter_by(id=id).first()
    cart_form = CartForm(product.stock)
    review_form = ReviewForm()
    if current_user.is_authenticated and review_form.validate_on_submit():
        find_product_review = ProductReview.query.filter_by(product=product, user=current_user).first()
        if find_product_review:
            with app.app_context():
                db.session.delete(find_product_review)
                db.session.commit()
        new_product_review = ProductReview(
            user = current_user,
            product = product,
            rating = int(request.form.get('rating')),
            review = request.form.get('body')
        )
        with app.app_context():
            db.session.add(new_product_review)
            db.session.commit()
        return redirect(url_for('get_product', id=id))
    return render_template(
        'product_manager.html',
        cart_form=cart_form, 
        review_form=review_form, 
        product=product, 
        purpose = 'get'
    )

# // ------------------------------ CART FUNCTIONS ------------------------------ //

@app.route('/cart/<int:user_id>/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id, user_id):
    product = Product.query.filter_by(id=product_id).first()
    if int(request.form.get('count')) > product.stock:
        return redirect(url_for('home'))
    new_order = Order(
        user= current_user,
        product = product,
        quantity = int(request.form.get('count'))
    )
    with app.app_context():
        product.stock-=new_order.quantity
        db.session.add(new_order)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/cart/<int:user_id>')
@login_required
@member_only
def get_cart(user_id):
    orders = Order.query.filter_by(user=current_user)
    if user_id != current_user.id:
        return abort(403)
    return render_template('cart.html', orders = orders)

@app.route('/cart/<int:user_id>/increment_quantity/<int:product_id>')
@login_required
@member_only
def increment_product_quantity(user_id, product_id):
    if user_id != current_user.id:
        return abort(403)
    product = Product.query.filter_by(id=product_id).first()
    order = Order.query.filter_by(user_id=user_id, product_id=product_id).first()
    with app.app_context():
        order.quantity+=1
        product.stock-=1
        db.session.commit()
    return redirect(url_for('get_cart', user_id=user_id))

@app.route('/cart/<int:user_id>/decrement_quantity/<int:product_id>')
@login_required
@member_only
def decrement_product_quantity(user_id, product_id):
    if user_id != current_user.id:
        return abort(403)
    product = Product.query.filter_by(id=product_id).first()
    order = Order.query.filter_by(user_id=user_id, product_id=product_id).first()
    with app.app_context():
        order.quantity-=1
        product.stock+=1
        if order.quantity == 0:
            db.session.delete(order)
        db.session.commit()
    return redirect(url_for('get_cart', user_id=user_id))

# // ------------------------------ CHECKOUT ------------------------------ //

@app.route('/cart/<int:user_id>/checkout', methods=['GET', 'POST'])
@login_required
@member_only
def checkout(user_id):
    if user_id != current_user.id:
        return abort(403)
    details = Order.query.filter_by(user=current_user)
    transaction_id = 0
    form = TransactionForm()
    if form.validate_on_submit():
        with app.app_context():
            new_transaction = Transaction(
                user = current_user,
                date = datetime.now().date(),
                payment_method = request.form.get('payment_method'),
                payment_status = 'Unpaid',
                address = request.form.get('address'),
                delivery_cost = len(request.form.get('address'))*100,
                delivery_status = 'Unsent',
            )
            db.session.add(new_transaction)
            db.session.commit()
            for detail in details:
                new_transaction_detail = TransactionDetail(
                    transaction = new_transaction,
                    product = detail.product,
                    quantity = detail.quantity,
                    price = detail.product.price
                )
                db.session.add(new_transaction_detail)
                db.session.commit()
            for detail in details:
                db.session.delete(detail)
                db.session.commit()
            transaction_id = new_transaction.id  
        return redirect(url_for('get_transaction_history', user_id = user_id, transaction_id = transaction_id))    
    return render_template('checkout.html', form=form, details=details)

# // ------------------------------ TRANSACTION HISTORY ------------------------------ //

@app.route('/history/<int:user_id>')
@login_required
@member_only
def get_all_transactions(user_id):
    if user_id != current_user.id:
        return abort(403)
    transactions = Transaction.query.filter_by(user_id=user_id)
    return render_template('transaction.html', transactions = transactions, purpose='show_all')

@app.route('/history/<int:user_id>/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
@member_only
def get_transaction_history(user_id, transaction_id):
    if user_id != current_user.id:
        return abort(403)
    transaction = Transaction.query.filter_by(id=transaction_id).first()
    return render_template('transaction.html', transaction = transaction, purpose='single')

@app.route('/history/<int:user_id>/<int:transaction_id>/delivered', methods=['GET', 'POST'])
@login_required
@member_only
def product_delivered(user_id, transaction_id):
    if user_id != current_user.id:
        return abort(403)
    transaction = Transaction.query.filter_by(id=transaction_id).first()
    with app.app_context():
        transaction.delivery_status = 'Delivered'
        transaction.payment_status = 'Paid'
        db.session.commit()
    return redirect(url_for('get_transaction_history', user_id=user_id, transaction_id=transaction_id))

# // ------------------------------ DRIVER CODE ------------------------------ //

if __name__ == '__main__':
    app.run(debug=True)