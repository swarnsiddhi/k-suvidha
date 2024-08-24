from flask import Flask, jsonify, render_template, request
import csv
from geopy.distance import geodesic

app = Flask(__name__)

# Load data from CSV files
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

@app.route('/')
def index():
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
    app.run(debug=True)
