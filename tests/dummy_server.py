# just a basic flask app test

from flask import Flask, abort, request, jsonify

app = Flask(__name__)

@app.route('/', methods=["GET", "POST"])
def test():
    if request.method == 'POST':
        # Handle a simple prompt request
        prompt = request.form.get('prompt')
        if prompt:
            output = generate_text(prompt)
            return jsonify({'output': output})
    
        # Handle a JSON request
        if request.headers['Content-Type'] == 'application/json':
            data = request.get_json()
            messages = data.get('messages')
            if messages:
                for message in messages:
                    role = message.get('role')
                    content = message.get('content')
                    # Process the message here
                    # You can access the role and content variables
                    # and perform any required actions
                    print(f"Received message from {role}: {content}")
                return 'Message received successfully'
            else:
                abort(400, 'Invalid JSON request')
    
    return 'Invalid request', 400

if __name__ == '__main__':
    app.run()
