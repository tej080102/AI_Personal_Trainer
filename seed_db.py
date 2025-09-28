import random
import datetime
from db import init_db, save_workout, create_user

# Initialize DB
init_db()

USER_ID = "testuser"
PASSWORD = "password123"

# Create the user (hashed password)
create_user(USER_ID, PASSWORD)

strength_exercises = ["bench press", "squats", "deadlift", "overhead press", "barbell row", "pushups", "pullups"]
cardio_exercises = ["running", "cycling", "rowing"]

today = datetime.date.today()

for day in range(1, 21):
    d = (today - datetime.timedelta(days=day)).isoformat()

    # Strength
    for _ in range(random.randint(0, 2)):
        ex = random.choice(strength_exercises)
        sets = random.randint(2, 5)
        reps = [random.randint(6, 12) for __ in range(sets)]
        weight = None if ex in ["pushups", "pullups"] else round(random.uniform(30, 100), 1)

        save_workout({
            "user_id": USER_ID,
            "date": d,
            "exercise": ex,
            "sets": sets,
            "reps": reps,
            "weight": weight,
            "distance": None,
            "duration": None,
        })

    # Cardio
    if random.random() < 0.5:
        ex = random.choice(cardio_exercises)
        dist = round(random.uniform(3, 10), 1)
        dur = round(dist * random.uniform(5.0, 7.0), 1)
        save_workout({
            "user_id": USER_ID,
            "date": d,
            "exercise": ex,
            "sets": None,
            "reps": None,
            "weight": None,
            "distance": dist,
            "duration": dur,
        })

print(f"✅ Seed data inserted for user '{USER_ID}' (password: {PASSWORD})")
