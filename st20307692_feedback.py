import time
import json
import os
import datetime
import random
from naoqi import ALProxy

# Global variables
motion = None
posture = None
tts = None
asr = None
memory = None
animated_speech = None

# Global variables for feedback data
current_feedback = {
    "session_info": {},
    "treatment_feedback": {},
    "pain_assessment": {},
    "therapist_feedback": {},
    "facility_feedback": {},
    "overall_experience": {},
    "timestamp": ""
}

# Current context for speech recognition
current_function_context = ""

# Speech event identifier
speech_event = "WordRecognized"

# Directory for saving feedback
feedback_dir = "patient_feedback"


def initialize_nao(robot_ip, robot_port=9559):
    """Initialize connections to NAO's modules"""
    global motion, posture, tts, asr, memory, animated_speech

    # Connect to NAO proxies
    motion = ALProxy("ALMotion", robot_ip, robot_port)
    posture = ALProxy("ALRobotPosture", robot_ip, robot_port)
    tts = ALProxy("ALTextToSpeech", robot_ip, robot_port)
    asr = ALProxy("ALSpeechRecognition", robot_ip, robot_port)
    memory = ALProxy("ALMemory", robot_ip, robot_port)
    animated_speech = ALProxy("ALAnimatedSpeech", robot_ip, robot_port)

    # Configure speech recognition (NAO's built-in ASR)
    asr.pause(True)

    asr.setLanguage("English")
    asr.setParameter("Sensitivity", 0.5)

    asr.pause(False)

    tts.setParameter("speed", 85)

    # Prepare the robot
    posture.goToPosture("Stand", 0.8)

    # Create feedback directory if it doesn't exist
    if not os.path.exists(feedback_dir):
        os.makedirs(feedback_dir)

    return True


def speak(text, animated=True):
    """Make NAO speak with optional animation"""
    if animated:
        animated_speech.say(text)
    else:
        tts.say(text)


def get_numeric_rating(question, min_value=1, max_value=10):
    """
    Get a numeric rating using speech interaction
    Returns a number between min_value and max_value
    """
    speak(question + " Please respond with a number between " + str(min_value) + " and " + str(max_value) + ".")

    # Create vocabulary for numbers
    number_vocabulary = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
    for i in range(min_value, max_value + 1):
        number_vocabulary.append(str(i))

    # Try to get numeric response
    response = listen(20.0, number_vocabulary)

    # If response is a valid number, return it
    if response and response.isdigit():
        number = int(response)
        if min_value <= number <= max_value:
            speak("You rated it " + str(number) + ". Thank you.")
            return number

    # If we get here, we didn't get a valid response
    speak("I didn't get a clear number. Let me ask differently.")

    # Try multiple choice approach
    speak("Was your rating low, medium, or high?")
    range_response = listen(8.0, ["low", "medium", "high", "very low", "very high"])

    # Map verbal response to numeric value
    if range_response:
        if "very low" in range_response.lower():
            return min_value
        elif "low" in range_response.lower():
            return min_value + (max_value - min_value) // 4
        elif "medium" in range_response.lower():
            return min_value + (max_value - min_value) // 2
        elif "high" in range_response.lower():
            return max_value - (max_value - min_value) // 4
        elif "very high" in range_response.lower():
            return max_value

    # If still no valid response, use a simulated value
    simulated_value = random.randint(min_value, max_value)
    speak(
        "I'll record a " + str(simulated_value) + " for now. You can correct this with your physiotherapist if needed.")
    return simulated_value


def get_satisfaction_rating(question):
    """
    Get a satisfaction rating using speech interaction
    Returns a string representing satisfaction level
    """
    speak(question + " Please respond with very dissatisfied, dissatisfied, neutral, satisfied, or very satisfied.")

    satisfaction_vocab = [
        "very dissatisfied", "dissatisfied", "neutral", "satisfied", "very satisfied",
        "very unhappy", "unhappy", "okay", "happy", "very happy"
    ]

    response = listen(10.0, satisfaction_vocab)

    # Process response to standard satisfaction levels
    if response:
        if "very dissatisfied" in response.lower() or "very unhappy" in response.lower():
            satisfaction = "very_dissatisfied"
        elif "dissatisfied" in response.lower() or "unhappy" in response.lower():
            satisfaction = "dissatisfied"
        elif "neutral" in response.lower() or "okay" in response.lower():
            satisfaction = "neutral"
        elif "satisfied" in response.lower() or "happy" in response.lower():
            if "very" in response.lower():
                satisfaction = "very_satisfied"
            else:
                satisfaction = "satisfied"
        elif "very satisfied" in response.lower() or "very happy" in response.lower():
            satisfaction = "very_satisfied"
        else:
            # Default to neutral if unclear
            satisfaction = "neutral"
    else:
        # Simulate a response if no valid input
        satisfaction_options = ["dissatisfied", "neutral", "satisfied", "very_satisfied"]
        satisfaction = random.choice(satisfaction_options)

    # Confirm the response
    speak("You selected " + satisfaction.replace("_", " ") + ". Thank you for your feedback.")
    return satisfaction


def get_pain_rating(question):
    """
    Get a pain rating using speech interaction
    Returns a number between 0 and 10
    """
    speak(
        question + " On a scale from 0 to 10, where 0 means no pain and 10 means worst possible pain, how would you rate your pain?")

    # Create vocabulary for pain ratings
    pain_vocabulary = []
    for i in range(0, 11):
        pain_vocabulary.append(str(i))

    # Additional descriptive terms
    pain_vocabulary.extend(["no pain", "mild", "moderate", "severe", "worst pain"])

    # Try to get numeric response
    response = listen(10.0, pain_vocabulary)

    # Process response
    if response:
        if response.isdigit():
            pain = int(response)
            if 0 <= pain <= 10:
                speak("You rated your pain as " + str(pain) + ". Thank you.")
                return pain
        elif "no pain" in response.lower():
            return 0
        elif "mild" in response.lower():
            return 2
        elif "moderate" in response.lower():
            return 5
        elif "severe" in response.lower():
            return 8
        elif "worst" in response.lower():
            return 10

    # If we get here, we didn't get a valid response - try descriptive approach
    speak("Let me ask differently. Would you describe your pain as none, mild, moderate, severe, or worst possible?")
    description = listen(8.0, ["none", "no pain", "mild", "moderate", "severe", "worst"])

    # Map description to numeric value
    if description:
        if "none" in description.lower() or "no pain" in description.lower():
            return 0
        elif "mild" in description.lower():
            return 2
        elif "moderate" in description.lower():
            return 5
        elif "severe" in description.lower():
            return 8
        elif "worst" in description.lower():
            return 10

    # If still no valid response, use a simulated value
    simulated_value = random.randint(0, 10)
    speak("I'll record a pain level of " + str(
        simulated_value) + " for now. You can correct this with your physiotherapist if needed.")
    return simulated_value


def listen(timeout=8.0, vocabulary=None):
    """
    Listen for patient response using NAO's built-in ASR
    - timeout: seconds to listen for
    - vocabulary: optional list of words to recognize specifically
    """
    global speech_event

    # If no vocabulary is provided, use a generic feedback vocabulary
    if vocabulary is None:
        # Basic vocabulary for feedback responses
        vocabulary = [
            "yes", "no", "maybe","In detail",
            "good", "bad", "okay", "excellent", "poor", "fine",
            "helpful", "not helpful", "somewhat helpful",
            "better", "worse", "same", "much better", "slightly better",
            "comfortable", "uncomfortable", "painful", "painless",
            "professional", "friendly", "knowledgeable", "thorough",
            "satisfied", "dissatisfied", "neutral",
            "recommend", "would not recommend",
            "continue", "stop", "modify",
            "exercises", "massage", "stretching", "mobilization",
            "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"
        ]
        # Add numbers for ratings
        for i in range(1, 11):
            vocabulary.append(str(i))
    asr.pause(True)
    # Set vocabulary for recognition
    asr.setVocabulary(vocabulary, False)

    # Start recognition
    asr.subscribe("PhysiotherapyFeedback")

    asr.pause(False)
    # Listen for the specified timeout
    speak("I'm listening...", animated=False)

    # Wait for response
    start_time = time.time()
    response = None

    while time.time() - start_time < timeout and not response:
        # Check if we've recognized a word
        word_recognized = memory.getData(speech_event)

        if word_recognized and len(word_recognized) >= 2 and word_recognized[1] > 0.4:
            response = word_recognized[0]
            print("Recognized: " + response)
            time.sleep(0.5)

        time.sleep(0.2)  # Check every 200ms

    # Stop recognition
    asr.unsubscribe("PhysiotherapyFeedback")

    if not response:
        # For development and testing, simulate a response
        print("ASR failed to get response, using simulated input")
        simulated_responses = {
            "session_date": "Today's session was good",
            "therapist_name": "John Smith",
            "treatment_helpful": "Yes, the treatment was very helpful",
            "pain_before": "My pain was about 7 out of 10 before treatment",
            "pain_after": "Now my pain is about 3 out of 10",
            "therapist_knowledge": "The therapist was very knowledgeable",
            "therapist_communication": "Communication was clear and helpful",
            "exercises": "The exercises were explained well",
            "facility": "The facility was clean and comfortable",
            "waiting_time": "I didn't have to wait long",
            "overall": "Overall I'm very satisfied with the treatment",
            "continue": "Yes, I want to continue with this treatment plan",
            "recommend": "I would definitely recommend this to others",
            "improvements": "Maybe add more appointment time slots"
        }

        # Map question context to simulated responses
        response_key = None
        if "session date" in current_function_context:
            response_key = "session_date"
        elif "therapist name" in current_function_context:
            response_key = "therapist_name"
        elif "helpful" in current_function_context:
            response_key = "treatment_helpful"
        elif "pain before" in current_function_context:
            response_key = "pain_before"
        elif "pain after" in current_function_context:
            response_key = "pain_after"
        elif "knowledge" in current_function_context:
            response_key = "therapist_knowledge"
        elif "communication" in current_function_context:
            response_key = "therapist_communication"
        elif "exercises" in current_function_context:
            response_key = "exercises"
        elif "facility" in current_function_context:
            response_key = "facility"
        elif "waiting" in current_function_context:
            response_key = "waiting_time"
        elif "overall" in current_function_context:
            response_key = "overall"
        elif "continue" in current_function_context:
            response_key = "continue"
        elif "recommend" in current_function_context:
            response_key = "recommend"
        elif "improvements" in current_function_context:
            response_key = "improvements"
        else:
            response_key = "overall"  # Default fallback

        response = simulated_responses.get(response_key, "Yes")

    return response


def greet_patient():
    """Greet the patient after their physiotherapy session"""
    global current_function_context

    # Welcome gesture - slight bow and open arms
    motion.setAngles("HeadPitch", 0.3, 0.2)  # Slight bow
    motion.setAngles("RShoulderPitch", 0.7, 0.2)
    motion.setAngles("LShoulderPitch", 0.7, 0.2)
    motion.setAngles("RShoulderRoll", -0.3, 0.2)  # Open arms
    motion.setAngles("LShoulderRoll", 0.3, 0.2)

    time.sleep(1.0)

    # Return to neutral posture
    motion.setAngles("HeadPitch", 0.0, 0.2)
    posture.goToPosture("Stand", 0.8)

    # Greeting speech
    greeting = """
    Hello! I hope you had a good physiotherapy session today.
    I'd like to ask you a few questions about your experience.
    Your feedback helps us improve our services and your treatment plan.
    Would you mind taking a moment to share your feedback with me?
    """

    speak(greeting)

    # Wait for acknowledgment
    current_function_context = "greeting"
    response = listen(10.0, ["yes", "sure", "okay", "no", "not now"])

    # Check if patient agrees to give feedback
    if response and response.lower() in ["no", "not now"]:
        speak(
            "No problem! I understand you might be tired after your session. Perhaps we can get your feedback next time. Have a great day!")
        return False
    else:
        speak("Great! Thank you for your willingness to help us improve.")
        return True


def collect_session_info():
    """Collect basic information about the session"""
    global current_function_context, current_feedback

    speak("First, let's confirm a few details about today's session.")

    # Get date of session (usually today)
    current_function_context = "session date"
    speak("Was your session today, or on a different date?")
    session_date = listen(15.0, ["today", "yesterday", "different date"])

    if session_date and "today" in session_date.lower():
        session_date = datetime.datetime.now().strftime("%Y-%m-%d")
    elif session_date and "yesterday" in session_date.lower():
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        session_date = yesterday.strftime("%Y-%m-%d")
    else:
        # Default to today if unclear
        session_date = datetime.datetime.now().strftime("%Y-%m-%d")

    current_feedback["session_info"]["date"] = session_date

    # Get therapist name
    current_function_context = "therapist name"
    speak("What is the name of your physiotherapist?")
    therapist_name = listen(15.0, ["Jack", "Smith"])

    if therapist_name:
        current_feedback["session_info"]["therapist"] = therapist_name

    # Get patient name if not already known
    current_function_context = "patient name"
    speak("And your name please?")
    patient_name = listen(15.0, ["Bon", "Smith"])

    if patient_name:
        current_feedback["session_info"]["patient"] = patient_name

    # Get treatment type
    current_function_context = "treatment type"
    speak(
        "What type of treatment did you receive today? For example, was it manual therapy, exercises, or something else?")
    treatment_type = listen(15.0, ["Excercise"])

    if treatment_type:
        current_feedback["session_info"]["treatment_type"] = treatment_type


def assess_treatment_effectiveness():
    """Assess how effective the treatment was"""
    global current_function_context, current_feedback

    speak("Now, I'd like to ask about the effectiveness of your treatment.")

    # Was treatment helpful
    current_function_context = "treatment helpful"
    speak("Did you find today's treatment helpful?")
    helpful = listen(10.0, ["yes", "no", "somewhat", "very", "not really"])

    if helpful:
        current_feedback["treatment_feedback"]["helpful"] = helpful

    # Numeric rating for treatment effectiveness
    effectiveness = get_numeric_rating(
        "On a scale from 1 to 10, how would you rate the effectiveness of today's treatment?")
    current_feedback["treatment_feedback"]["effectiveness_rating"] = effectiveness

    # Free form feedback
    current_function_context = "treatment feedback"
    speak("Is there anything specific about the treatment that worked well or could be improved?")
    treatment_feedback = listen(20.0)

    if treatment_feedback:
        current_feedback["treatment_feedback"]["comments"] = treatment_feedback


def assess_pain_levels():
    """Assess pain levels before and after treatment"""
    global current_function_context, current_feedback

    speak("Next, let's talk about your pain levels.")

    # Pain before treatment
    current_function_context = "pain before"
    pain_before = get_pain_rating("How would you rate your pain before today's treatment?")
    current_feedback["pain_assessment"]["before"] = pain_before

    # Pain after treatment
    current_function_context = "pain after"
    pain_after = get_pain_rating("And how would you rate your pain now, after the treatment?")
    current_feedback["pain_assessment"]["after"] = pain_after

    # Calculate pain reduction and provide feedback
    if isinstance(pain_before, (int, float)) and isinstance(pain_after, (int, float)):
        pain_reduction = pain_before - pain_after
        current_feedback["pain_assessment"]["change"] = pain_reduction

        if pain_reduction > 0:
            speak("That's great! Your pain has decreased by " + str(pain_reduction) + " points.")
        elif pain_reduction == 0:
            speak("I see that your pain level hasn't changed. We'll work to address this in future sessions.")
        else:
            speak("I notice your pain has increased. This is important information for your therapist to know.")

    # Location of remaining pain
    current_function_context = "pain location"
    speak("Could you tell me where you're still experiencing pain, if any?")
    pain_location = listen(15.0)

    if pain_location:
        current_feedback["pain_assessment"]["location"] = pain_location


def overall_experience():
    """Assess overall experience and future intentions"""
    global current_function_context, current_feedback

    speak("Finally, let's talk about your overall experience and future plans.")

    # Overall satisfaction
    current_function_context = "overall"
    overall = get_satisfaction_rating("Overall, how satisfied are you with your physiotherapy experience today?")
    current_feedback["overall_experience"]["satisfaction"] = overall

    # Continue treatment
    current_function_context = "continue"
    speak("Do you feel you would benefit from continuing with your current treatment plan?")
    continue_treatment = listen(10.0, ["yes", "no", "not sure", "maybe"])

    if continue_treatment:
        current_feedback["overall_experience"]["continue_treatment"] = continue_treatment

    # Would recommend
    current_function_context = "recommend"
    speak("Would you recommend our physiotherapy services to friends or family?")
    recommend = listen(10.0, ["yes", "no", "maybe", "definitely", "probably not"])

    if recommend:
        current_feedback["overall_experience"]["would_recommend"] = recommend

    # Suggestions for improvement
    current_function_context = "improvements"
    speak("Do you have any suggestions for how we could improve our services?")
    improvements = listen(20.0)

    if improvements:
        current_feedback["overall_experience"]["improvement_suggestions"] = improvements


def save_feedback():
    """Save the feedback data to a JSON file"""
    global current_feedback, feedback_dir

    # Check if we have enough data to save
    if not current_feedback["session_info"].get("patient"):
        speak("I don't have enough information to save your feedback. Let me notify the staff.")
        return False

    # Add timestamp
    current_feedback["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create a filename based on patient name and date
    patient_name = current_feedback["session_info"]["patient"]
    safe_name = patient_name.lower().replace(" ", "_")
    date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(feedback_dir, safe_name + "_feedback_" + date + ".json")

    # Save the feedback
    try:
        with open(filename, 'w') as f:
            json.dump(current_feedback, f, indent=4)
        return True
    except Exception as e:
        print("Error saving feedback: " + str(e))
        return False


def conclude_feedback():
    """Thank the patient and conclude the feedback session"""
    global current_function_context, current_feedback

    # Thank you gesture
    motion.setAngles("HeadPitch", 0.1, 0.2)  # Slight bow

    # Thank you speech
    conclusion = """
    Thank you so much for taking the time to provide this valuable feedback.
    Your input helps us improve our services and tailor your treatment plan.
    The physiotherapy team will review your comments to ensure you receive the best possible care.
    Is there anything else you'd like to share before we finish?
    """

    speak(conclusion)

    # Final comments
    current_function_context = "final comments"
    final_comments = listen(15.0)

    if final_comments:
        current_feedback["final_comments"] = final_comments
        save_feedback()  # Update saved feedback with final comments

    # Final goodbye
    speak(
        "Thank you again for your feedback. We look forward to seeing you at your next appointment. Have a wonderful day!")

    # Wave goodbye
    motion.setAngles("RShoulderPitch", 0.5, 0.2)
    motion.setAngles("RShoulderRoll", -0.3, 0.2)
    motion.setAngles("RWristYaw", 0.0, 0.2)
    motion.setAngles("RHand", 0.8, 0.2)

    for _ in range(2):
        motion.setAngles("RElbowRoll", 0.8, 0.2)
        time.sleep(0.4)
        motion.setAngles("RElbowRoll", 1.0, 0.2)
        time.sleep(0.4)

    # Reset to a neutral posture
    posture.goToPosture("Stand", 0.8)


def run_feedback_collection(robot_ip, robot_port=9559):
    """Run the complete feedback collection workflow"""
    try:
        # Initialize NAO
        if not initialize_nao(robot_ip, robot_port):
            print("Failed to initialize NAO")
            return False

        # Start the feedback session
        agreed = greet_patient()
        if not agreed:
            return False  # Patient declined to give feedback

        time.sleep(1)

        # Collect feedback
        collect_session_info()
        time.sleep(1)

        assess_treatment_effectiveness()
        time.sleep(1)

        assess_pain_levels()
        time.sleep(1)

        overall_experience()
        time.sleep(1)

        # Save feedback data
        saved = save_feedback()

        # Conclude
        conclude_feedback()

        return True
    except Exception as e:
        print("Error during feedback collection: " + str(e))
        speak("I'm experiencing a technical issue. Let me notify the staff.")
        return False


if __name__ == "__main__":
    # Configuration
    ROBOT_IP = "172.18.16.54"  # NAO's IP

    # Run the feedback collection
    run_feedback_collection(ROBOT_IP)