from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

GROQ_API_KEY = os.getenv('GROQ_API_KEY')

@app.route('/api/diet', methods=['POST', 'OPTIONS'])
def get_diet():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return '', 200
        
    app.logger.debug('Received a POST request to /api/diet')
    
    data = request.json
    if not data:
        app.logger.error('No JSON data received in the request')
        return jsonify({"error": "No data provided"}), 400

    age = data.get('age')
    weight = data.get('weight')
    history = data.get('history')
    
    if not age or not weight or not history:
        app.logger.error('Missing required fields: age, weight, or history')
        return jsonify({"error": "Missing required fields: age, weight, or history"}), 400

    diet_type = data.get('dietType', 'Veg')  # Default: Veg
    app.logger.debug(f'Client prefers a {diet_type.lower()} diet')

    diet_type = diet_type.lower()
    diet_guidelines = ""
    
    if diet_type == "veg":
        diet_guidelines = """
STRICT DIETARY RULES (VEGETARIAN):
- ❌ FORBIDDEN: All meat, poultry, fish, and seafood
- ✅ ALLOWED: Dairy products, eggs, plant-based foods
- Every meal MUST comply with vegetarian restrictions
"""
    elif diet_type == "vegan":
        diet_guidelines = """
STRICT DIETARY RULES (VEGAN):
- ❌ FORBIDDEN: All animal products (meat, fish, dairy, eggs, honey)
- ✅ ALLOWED: Only plant-based foods (vegetables, fruits, grains, legumes, nuts, seeds)
- Every meal MUST comply with vegan restrictions
- Double-check all ingredients to ensure no animal derivatives
"""
    elif diet_type == "nonveg":
        diet_guidelines = """
DIETARY RULES (NON-VEGETARIAN):
- ✅ ALLOWED: All foods including meat, poultry, fish, eggs, and dairy
- Include a balanced mix of protein sources
"""
    else:
        app.logger.warning(f"Received an unrecognized diet type: {diet_type}")

    prompt = f"""You are creating a 7-day {diet_type} diet plan with ZERO introduction, explanation, or disclaimers.

Client details:
- Age: {age}
- Weight: {weight} kg
- Medical History: {history}

{diet_guidelines}

CONTENT RESTRICTIONS:
- ⛔ DO NOT include any greetings, introductions, or conclusions
- ⛔ DO NOT include any professional commentary
- ⛔ DO NOT explain your reasoning or choices

OUTPUT FORMAT:
Return ONLY a structured meal plan with this exact format for 7 days:

Day 1:
- Breakfast: [specific foods and portions]
- Lunch: [specific foods and portions]
- Dinner: [specific foods and portions]
- Snacks: [specific foods and portions]

Day 2:
- Breakfast: [specific foods and portions]
- Lunch: [specific foods and portions]
- Dinner: [specific foods and portions]
- Snacks: [specific foods and portions]

(Continue similarly up to Day 7)
"""

    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json',
    }
    system_message = f"You are a professional dietician specialized in {diet_type} diets. Follow the user's instructions EXACTLY."

    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2 
    }
    
    try:
        app.logger.debug(f'Sending request to Groq API with payload: {payload}')
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        
        if res.status_code != 200:
            app.logger.error(f"Failed to fetch from Groq API: {res.text}")
            return jsonify({"error": f"Failed to fetch from Groq API: {res.text}"}), res.status_code
        
        result = res.json()["choices"][0]["message"]["content"]
        app.logger.debug(f"Received response from Groq API: {result[:100]}...")  # Log first 100 characters
        
        if diet_type == "veg" and any(item in result.lower() for item in ["chicken", "beef", "pork", "fish", "salmon", "tuna", "meat", "seafood"]):
            app.logger.error('Generated diet contains non-vegetarian items despite vegetarian request')
            return jsonify({"error": "Generated diet contains non-vegetarian items. Please try again."}), 400
        
        if diet_type == "vegan" and any(item in result.lower() for item in ["milk", "cheese", "yogurt", "cream", "butter", "egg", "honey", "chicken", "beef", "pork", "fish"]):
            app.logger.error('Generated diet contains non-vegan items despite vegan request')
            return jsonify({"error": "Generated diet contains non-vegan items. Please try again."}), 400

        return jsonify({"plan": result})
    
    except Exception as e:
        app.logger.exception("An error occurred while processing the diet plan request")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)