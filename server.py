from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import requests
import pandas as pd
from io import StringIO
import csv
from datagovindia import DataGovIndia
from geopy.distance import geodesic

app = Flask(__name__)

SAVE_DIRECTORY = 'saved_files'
IMAGE_DIRECTORY = 'static/images'
CSV_FILE_PATH = 'crop_data.csv'  # Path to your CSV file
API_KEY = "1e441d8391794534b9bbf4e9ca6dd4ea"  # Your Weatherbit API key
datagovin = DataGovIndia(api_key="579b464db66ec23bdd00000186bc564ca97b4f3270379f675cdae62a")

# Ensure directories exist
if not os.path.exists(SAVE_DIRECTORY):
    os.makedirs(SAVE_DIRECTORY)

if not os.path.exists(IMAGE_DIRECTORY):
    os.makedirs(IMAGE_DIRECTORY)

def load_crops_from_csv(file_path):
    crops = {}
    with open(file_path, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            crop_name = row['crop']
            if crop_name not in crops:
                crops[crop_name] = []
            crops[crop_name].append({
                'type': row['type'],
                'description': row['description'],
                'imageUrl': row['image url']
            })
    return crops

# Load crops data from CSV file
crops_data = load_crops_from_csv(CSV_FILE_PATH)

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/marketplace')
def marketplace():
    return render_template('marketplace.html', crops=load_crops_from_csv(CSV_FILE_PATH))

@app.route('/save-json', methods=['POST'])
def save_json():
    data = request.get_json()
    file_name = data.get('fileName')
    content = data.get('content')

    # Convert JSON content to CSV format
    csv_data = []
    csv_data.append(['product', 'seller', 'quantity'])  # CSV headers
    content_dict = eval(content)
    csv_data.append([content_dict['product'], content_dict['seller'], content_dict['quantity']])

    file_path = os.path.join(SAVE_DIRECTORY, file_name.replace('.json', '.csv'))

    try:
        # Save as CSV
        with open(file_path, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
        return jsonify({'success': True, 'message': 'File saved successfully'}), 200
    except Exception as e:
        print(f'Error saving file: {e}')
        return jsonify({'success': False, 'message': 'File could not be saved'}), 500

@app.route('/products/<crop_name>', methods=['GET'])
def get_products(crop_name):
    if crop_name in crops_data:
        return jsonify(crops_data[crop_name]), 200
    else:
        return jsonify({'error': 'Crop not found'}), 404

@app.route('/images/<filename>', methods=['GET'])
def get_image(filename):
    return send_from_directory(IMAGE_DIRECTORY, filename)

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = file.filename
    file.save(os.path.join(IMAGE_DIRECTORY, filename))

    return jsonify({'success': True, 'message': 'File uploaded successfully'}), 200

@app.route('/prices')
def prices():
    return render_template('prices.html')

@app.route('/fetch-gov-data', methods=['GET'])
def fetch_gov_data():
    try:
        # Fetch data from DataGovIndia
        raw_data = datagovin.get_data("9ef84268-d588-465a-a308-a864a43d0070")
        
        # Check if raw_data is a DataFrame
        if isinstance(raw_data, pd.DataFrame):
            df = raw_data
        else:
            # If it's not a DataFrame, handle it accordingly
            raise ValueError("Expected a DataFrame but received something else.")

        # Convert dataframe to JSON format
        json_data = df.to_dict(orient='records')

        return jsonify(json_data), 200
    except Exception as e:
        print(f'Error fetching government data: {e}')
        return jsonify({'error': 'Failed to fetch data'}), 500

def get_weather_forecast(city, api_key):
    base_url = "https://api.weatherbit.io/v2.0/forecast/daily"
    params = {
        "city": city,
        "key": api_key,
        "days": 7
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None

@app.route('/weather', methods=['GET'])
def weather():
    city = request.args.get('city', 'New Delhi')  # Use a default city if none is provided
    forecast_data = get_weather_forecast(city, API_KEY)
    if forecast_data:
        forecast = forecast_data['data']
        humidity = [day['rh'] for day in forecast]
        dates = [day['datetime'] for day in forecast]
        return render_template('weather.html', city=city, forecast=forecast, humidity=humidity, dates=dates)
    else:
        return "Error retrieving weather data", 500
    
def load_csv(filename):
    with open(filename, mode='r') as file:
        reader = csv.DictReader(file)
        return list(reader)

def save_csv(filename, data, fieldnames):
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

# Load the CSV files
equipment = load_csv('equipment.csv')
bookings = load_csv('bookings.csv')

@app.route('/rentals')
def rentals():
    # Render the main rental page
    return render_template('rental.html')

@app.route('/states')
def get_states():
    # Get unique states from the equipment CSV
    states = sorted(set(item['State'] for item in equipment))
    return jsonify(states)

@app.route('/districts/<state>')
def get_districts(state):
    # Get unique districts for the selected state
    districts = sorted(set(item['Location'] for item in equipment if item['State'] == state))
    return jsonify(districts)

@app.route('/equipment/<district>')
def get_equipment(district):
    # Get equipment for the selected district
    filtered_equipment = [item for item in equipment if item['Location'] == district]
    return jsonify(filtered_equipment)

@app.route('/nearby')
def find_nearby():
    lat = float(request.args.get('lat'))
    lng = float(request.args.get('lng'))
    user_location = (lat, lng)

    nearby_equipment = []

    for item in equipment:
        item_location = (float(item['Latitude']), float(item['Longitude']))
        distance = geodesic(user_location, item_location).km

        if distance <= 100:  # 100 km radius
            nearby_equipment.append(item)

    return jsonify(nearby_equipment)

@app.route('/equipment/info/<int:id>')
def get_equipment_info(id):
    # Get detailed equipment information by ID
    item = next((eq for eq in equipment if int(eq['id']) == id), None)
    if item:
        return jsonify({
            'Name': item['Name'],
            'NumberPlate': item['NumberPlate'],
            'Village': item['Village'],
            'District': item['Location'],
            'OwnerMobile': item['OwnerMobile'],
            'id': id
        })
    return jsonify({'error': 'Equipment not found'}), 404

@app.route('/rent/<int:id>', methods=['POST'])
def rent_equipment(id):
    global equipment, bookings

    item = next((eq for eq in equipment if int(eq['id']) == id), None)
    if item and item['AvailabilityStatus'] == 'Available':
        # Update equipment availability
        item['AvailabilityStatus'] = 'Rented'

        # Add a new booking
        new_booking = {
            'id': len(bookings) + 1,
            'EquipmentID': id,
            'UserID': 'some_user_id',  # Replace with the actual user ID
            'Status': 'Active'
        }
        bookings.append(new_booking)

        # Save changes to CSV files
        save_csv('equipment.csv', equipment, equipment[0].keys())
        save_csv('bookings.csv', bookings, bookings[0].keys())

        return jsonify({'success': True})
    return jsonify({'error': 'Equipment not available'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
