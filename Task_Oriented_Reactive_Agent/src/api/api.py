# api.py

from flask import Flask, request, jsonify
from data_store import (
    get_active_doctors_by_specialty,
    get_available_slots_by_doctor_id,
    mark_slot_as_booked,
    log_booking
)
from canonicalizers import canonicalize_specialty
from schemas import BookingRequest
from pydantic import ValidationError

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__) # Initialize the Flask application

# -------------------------
# GET DOCTORS
# -------------------------
@app.route("/doctors", methods=["GET"])
def get_doctors():
    specialty = request.args.get("specialty")
    specialty = canonicalize_specialty(specialty)

    if not specialty:
        return jsonify({"error": "specialty is required"}), 400
    
    doctors = get_active_doctors_by_specialty(specialty)
    logger.info(f"Fetching doctors for specialty: {specialty}")

    return jsonify({"doctors": doctors})


# -------------------------
# GET SLOTS
# -------------------------
@app.route("/slots", methods=["GET"])
def get_slots():
    doctor_id = request.args.get("doctor_id")

    if not doctor_id:
        return jsonify({"error": "doctor_id is required"}), 400

    slots = get_available_slots_by_doctor_id(doctor_id)
    logger.warning("Missing required fields")

    return jsonify({"slots": slots})


# -------------------------
# BOOK APPOINTMENT
# -------------------------
@app.route("/book", methods=["POST"])
def book():
    try:
        raw_data = request.get_json()

        if not raw_data:
            logger.warning("Invalid or empty JSON received")
            return jsonify({"error": "Invalid JSON"}), 400
        
        # ✅ Schema validation happens here
        data = BookingRequest(**raw_data)

        logger.info(f"Booking request received for slot {data.slot_id}")


        success = mark_slot_as_booked(data["slot_id"])

        if not success:
            logger.warning(f"Slot already booked: {data.slot_id}")
            return jsonify({"error": "Slot already booked"}), 409

        log_booking(
            doctor_id=data["doctor_id"],
            slot_id=data["slot_id"],
            specialty=data["specialty"],
            patient_name=data["patient_name"]
        )

        logger.info(f"Booking successful for {data.patient_name}")

        return jsonify({
            "status": "CONFIRMED",
            "booking": data
        }), 200

    # ✅ Schema validation errors
    except ValidationError as ve:
        logger.error(f"Validation error: {ve}")
        return jsonify({
            "error": "Validation failed",
            "details": ve.errors()
        }), 400

    # ✅ Any unexpected errors
    except Exception as e:
        logger.error(f"Internal error: {e}")
        return jsonify({
            "error": "Internal server error"
        }), 500


if __name__ == "__main__":
    app.run(debug=True)