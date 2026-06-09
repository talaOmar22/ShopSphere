from flask import Flask, jsonify, request, render_template, redirect
from db import table
from boto3.dynamodb.conditions import Key
from datetime import datetime

app = Flask(__name__)

# --------------------
# HOME
# --------------------
@app.route('/')
def home():
    return render_template('index.html')

# --------------------
# CREATE PRODUCT
# --------------------
@app.route('/products', methods=['POST'])
def add_product():

    data = request.json

    if not data['name'].strip():
        return jsonify({"error": "Name is required"}), 400

    if float(data['price']) <= 0:
        return jsonify({"error": "Price must be greater than 0"}), 400

    if int(data['stock']) < 0:
        return jsonify({"error": "Stock cannot be negative"}), 400

    table.put_item(
        Item={
            "PK": f"PRODUCT#{data['id']}",
            "SK": "META",
            "name": data['name'],
            "category": data['category'],
            "price": data['price'],
            "stock": data['stock']
        }
    )

    return jsonify({"message": "Product added"})


# --------------------
# READ ALL PRODUCTS
# --------------------
@app.route('/products', methods=['GET'])
def get_products():

    response = table.scan()

    if len(response['Items']) == 0:
        return jsonify({"message": "Catalog is empty"})

    return jsonify(response['Items'])


# --------------------
# READ PRODUCT BY ID
# --------------------
@app.route('/products/<id>', methods=['GET'])
def get_product(id):

    response = table.get_item(
        Key={
            "PK": f"PRODUCT#{id}",
            "SK": "META"
        }
    )

    if 'Item' not in response:
        return jsonify({"error": "Product not found"}), 404

    return jsonify(response['Item'])


# --------------------
# UPDATE PRODUCT
# --------------------
@app.route('/products/<id>', methods=['PUT'])
def update_product(id):

    data = request.json

    table.update_item(
        Key={
            "PK": f"PRODUCT#{id}",
            "SK": "META"
        },
        UpdateExpression="SET price=:p, stock=:s",
        ExpressionAttributeValues={
            ":p": data['price'],
            ":s": data['stock']
        }
    )

    return jsonify({"message": "Product updated"})


# --------------------
# DELETE PRODUCT
# --------------------
@app.route('/products/<id>', methods=['DELETE'])
def delete_product(id):

    table.delete_item(
        Key={
            "PK": f"PRODUCT#{id}",
            "SK": "META"
        }
    )

    return jsonify({"message": "Product deleted"})


# --------------------
# FILTER BY CATEGORY (GSI)
# --------------------
@app.route('/products/category/<category>')
def get_by_category(category):

    response = table.query(
        IndexName='GSI1',
        KeyConditionExpression=Key('category').eq(category)
    )

    return jsonify(response['Items'])


# --------------------
# ADD REVIEW
# --------------------
@app.route('/products/<id>/reviews', methods=['POST'])
def add_review(id):

    data = request.json

    rating = int(data['rating'])

    if rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be between 1 and 5"}), 400

    table.put_item(
        Item={
            "PK": f"PRODUCT#{id}",
            "SK": f"REVIEW#{datetime.now().isoformat()}",
            "customer_name": data['customer_name'],
            "rating": rating,
            "comment": data['comment']
        }
    )

    return jsonify({"message": "Review added"})


# --------------------
# VIEW REVIEWS
# --------------------
@app.route('/products/<id>/reviews', methods=['GET'])
def get_reviews(id):

    response = table.query(
        KeyConditionExpression=
        Key('PK').eq(f'PRODUCT#{id}') &
        Key('SK').begins_with('REVIEW#'),
        ScanIndexForward=False
    )

    if len(response['Items']) == 0:
        return jsonify({"message": "No reviews yet"})

    return jsonify(response['Items'])


# --------------------
# AVERAGE RATING
# --------------------
@app.route('/products/<id>/average-rating', methods=['GET'])
def average_rating(id):

    response = table.query(
        KeyConditionExpression=
        Key('PK').eq(f'PRODUCT#{id}') &
        Key('SK').begins_with('REVIEW#')
    )

    reviews = response['Items']

    if len(reviews) == 0:
        return jsonify({"average_rating": 0})

    total = sum(int(review['rating']) for review in reviews)

    average = total / len(reviews)

    return jsonify({
        "average_rating": round(average, 2)
    })


# --------------------
# RUN APP
# --------------------
@app.route('/products-page')
def products_page():

    response = table.scan()

    products = [
        item for item in response['Items']
        if item['SK'] == 'META'
    ]

    return render_template(
        'products.html',
        products=products
    )

@app.route('/product/<id>')
def product_details(id):

    product_response = table.get_item(
        Key={
            "PK": f"PRODUCT#{id}",
            "SK": "META"
        }
    )

    if 'Item' not in product_response:
        return "Product not found"

    product = product_response['Item']

    reviews_response = table.query(
        KeyConditionExpression=
        Key('PK').eq(f'PRODUCT#{id}') &
        Key('SK').begins_with('REVIEW#'),
        ScanIndexForward=False
    )

    reviews = reviews_response['Items']

    average = 0

    if len(reviews) > 0:
        total = sum(int(review['rating']) for review in reviews)
        average = round(total / len(reviews), 2)

    return render_template(
        'product_details.html',
        product=product,
        reviews=reviews,
        average=average
    )
    
@app.route('/add-product', methods=['GET', 'POST'])
def add_product_form():

    if request.method == 'POST':

        table.put_item(
            Item={
                "PK": f"PRODUCT#{request.form['id']}",
                "SK": "META",
                "name": request.form['name'],
                "category": request.form['category'],
                "price": request.form['price'],
                "stock": request.form['stock']
            }
        )

        return redirect('/products-page')

    return render_template('add_product.html')

@app.route('/products-page/category/<category>')
def products_by_category(category):

    response = table.query(
        IndexName='GSI1',
        KeyConditionExpression=Key('category').eq(category)
    )

    return render_template(
        'products.html',
        products=response['Items']
    )
@app.route('/product/<id>/add-review', methods=['POST'])
def add_review_form(id):

    rating = int(request.form['rating'])

    if rating < 1 or rating > 5:
        return "Rating must be between 1 and 5"

    table.put_item(
        Item={
            "PK": f"PRODUCT#{id}",
            "SK": f"REVIEW#{datetime.now().isoformat()}",
            "customer_name": request.form['customer_name'],
            "rating": rating,
            "comment": request.form['comment']
        }
    )

    return redirect(f'/product/{id}')
@app.route('/delete-product/<id>')
def delete_product_page(id):

    table.delete_item(
        Key={
            "PK": f"PRODUCT#{id}",
            "SK": "META"
        }
    )

    return redirect('/products-page')
@app.route('/update-product/<id>', methods=['GET', 'POST'])
def update_product_page(id):

    if request.method == 'POST':

        table.update_item(
            Key={
                "PK": f"PRODUCT#{id}",
                "SK": "META"
            },
            UpdateExpression="""
            SET #n=:n,
                category=:c,
                price=:p,
                stock=:s
            """,
            ExpressionAttributeNames={
                "#n": "name"
            },
            ExpressionAttributeValues={
                ":n": request.form['name'],
                ":c": request.form['category'],
                ":p": request.form['price'],
                ":s": request.form['stock']
            }
        )

        return redirect(f'/product/{id}')

    response = table.get_item(
        Key={
            "PK": f"PRODUCT#{id}",
            "SK": "META"
        }
    )

    product = response['Item']

    return render_template(
        'update_product.html',
        product=product
    )

if __name__ == '__main__':
    app.run(debug=True)