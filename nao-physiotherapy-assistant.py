import time
import json
import os
import datetime
import requests
from naoqi import ALProxy


class PhysiotherapyAssistant(object):
    def __init__(self, robot_ip, robot_port=9559, ollama_url="http://localhost:11434"):
        """Initialize the NAO physiotherapy assistant"""
        # NAO proxies
        self.robot_ip = robot_ip
        self.robot_port = robot_port
        self.motion = ALProxy("ALMotion", robot_ip, robot_port)
        self.posture = ALProxy("ALRobotPosture", robot_ip, robot_port)
        self.tts = ALProxy("ALTextToSpeech", robot_ip, robot_port)
        self.asr = ALProxy("ALSpeechRecognition", robot_ip, robot_port)
        self.memory = ALProxy("ALMemory", robot_ip, robot_port)
        self.animated_speech = ALProxy("ALAnimatedSpeech", robot_ip, robot_port)

        # Configure speech recognition (NAO's built-in ASR)

        self.asr.pause(True)
        self.asr.setLanguage("English")
        # Increase word spotting sensitivity
        self.asr.setParameter("Sensitivity", 0.5)
        self.asr.pause(False)
        # Set NAO's voice speed
        self.tts.setParameter("speed", 85)

        # Initialize Ollama LLM API details
        self.ollama_url = ollama_url
        self.ollama_model = "mistral"  # Default model, can be changed to any model available in your Ollama instance

        # Patient data storage
        self.patients_dir = "patient_profiles"
        if not os.path.exists(self.patients_dir):
            os.makedirs(self.patients_dir)

        # Current patient information
        self.current_patient = {
            "personal_info": {},
            "medical_history": {},
            "physiotherapy_assessment": {},
            "session_notes": []
        }

        # Speech subscriber setup
        self.speech_event = "WordRecognized"

        # Current function context (for simulated responses)
        self.current_function_context = ""

        # Test Ollama connection
        try:
            self._test_ollama_connection()
            print("Successfully connected to Ollama LLM at " + ollama_url)
        except Exception as e:
            print("Warning: Could not connect to Ollama LLM: " + str(e))
            print("Make sure Ollama is running at " + ollama_url + " or speech interactions will be limited")

        # Prepare the robot
        self.posture.goToPosture("Stand", 0.8)

    def _test_ollama_connection(self):
        """Test connection to Ollama LLM"""
        test_prompt = "Respond with 'OK' if you can read this message."
        response = self._llm_interact(test_prompt)
        if "OK" not in response:
            raise Exception("Ollama response did not contain expected confirmation")

    def _speak(self, text, animated=True):
        """Make NAO speak with optional animation"""
        if animated:
            self.animated_speech.say(text)
        else:
            self.tts.say(text)

    def _listen(self, timeout=8.0, vocabulary=None):
        """
        Listen for patient response using NAO's built-in ASR
        - timeout: seconds to listen for
        - vocabulary: optional list of words to recognize specifically
        """
        #try:
        #   self.asr.unsubscribe("PhysiotherapyAssistant")
        #except:
        #     pass  # If already unsubscribed, that's fine
        # If no vocabulary is provided, use a generic large vocabulary
        # NAO's ASR works best with a defined vocabulary
        if vocabulary is None:
            # Basic vocabulary for general responses
            vocabulary = [
                "yes", "no", "maybe","father","Bob","Walking", "Lifting", "Running", "Legs", "Knee", "Jack", "Knee and Shoulder", "Shoulder"
                "good", "bad", "okay", "fine",
                "pain", "hurt", "sore", "ache",
                "left", "right", "arm", "leg", "back", "neck", "shoulder", "knee", "hip",
                "daily", "weekly", "sometimes", "always", "never",
                "mild", "moderate", "severe", "extreme",
                "walk", "sit", "stand", "lift", "climb", "bend",
                "medication", "surgery", "injury", "accident",
                "doctor", "hospital", "therapy", "treatment",
                "better", "worse", "same", "improving", "worsening",
                "exercise", "stretch", "mobility", "strength",
                "morning", "afternoon", "evening", "night",
                "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten","forty"
            ]
            # Add numbers for age, pain scale, etc.
            for i in range(1, 100):
                vocabulary.append(str(i))

        # Set vocabulary for recognition
        self.asr.pause(True)
        self.asr.setVocabulary(vocabulary, False)  # False means don't enable word spotting

        # Start recognition
        self.asr.subscribe("PhysiotherapyAssistant")
        self.asr.pause(False)
        # Listen for the specified timeout
        self._speak("I'm listening...", animated=False)

        # Wait for response
        start_time = time.time()
        response = None

        while time.time() - start_time < timeout and not response:
            # Check if we've recognized a word
            word_recognized = self.memory.getData(self.speech_event)

            # word_recognized is a list where first element is the word, second is confidence
            if word_recognized and len(word_recognized) >= 2 and word_recognized[1] > 0.4:
                response = word_recognized[0]
                print("Recognized: " + response)
                time.sleep(0.5)  # Brief pause to collect more words

                # For a real application, we would use a more sophisticated approach
                # to collect multiple words and form sentences.
                # Due to NAO's ASR limitations, we might need to use LLM to interpret
                # partial phrases or single words in context.

            time.sleep(0.2)  # Check every 200ms

        # Stop recognition
        self.asr.unsubscribe("PhysiotherapyAssistant")

        if not response:
            self._speak("I didn't catch that. Let's try a simpler approach.")
            # If formal ASR failed, try a basic yes/no question as fallback
            self._speak("Can you answer with just yes or no?")
            self.asr.pause(True)
            self.asr.setVocabulary(["yes", "no"], False)
            self.asr.subscribe("PhysiotherapyAssistant")
            self.asr.pause(False)
            start_time = time.time()
            while time.time() - start_time < 5.0 and not response:
                word_recognized = self.memory.getData(self.speech_event)
                if word_recognized and len(word_recognized) >= 2 and word_recognized[1] > 0.4:
                    response = word_recognized[0]
                time.sleep(0.2)

            self.asr.unsubscribe("PhysiotherapyAssistant")

        # Simulated response for development and testing
        # In a real environment, we'd use NAO's ASR more effectively
        # However, for complex medical conversations, we might need to
        # supplement with a tablet interface or external microphone

        # For this demo, we'll use simulated responses if NAO's ASR fails
        if not response:
            print("ASR failed to get response, using simulated input")
            # This is just for demonstration purposes
            simulated_responses = {
                "name": "John Smith",
                "age": "45",
                "phone": "555-123-4567",
                "emergency": "Mary Smith, wife, 555-987-6543",
                "conditions": "Lower back pain for 3 months, mild hypertension",
                "medications": "Ibuprofen occasionally, blood pressure medication daily",
                "surgeries": "No previous surgeries",
                "allergies": "No known allergies",
                "pain": "Lower back, worse on the right side",
                "pain_scale": "6 out of 10 when standing for long periods",
                "worse": "Sitting for long periods and bending forward",
                "activities": "Difficulty gardening and carrying groceries",
                "previous": "No previous physiotherapy",
                "goals": "I want to be able to garden again without pain and return to my walking routine"
            }

            # Map question context to simulated responses
            response_key = None
            if "name" in self.current_function_context:
                response_key = "name"
            elif "age" in self.current_function_context:
                response_key = "age"
            elif "phone" in self.current_function_context:
                response_key = "phone"
            elif "emergency" in self.current_function_context:
                response_key = "emergency"
            elif "medical condition" in self.current_function_context:
                response_key = "conditions"
            elif "medication" in self.current_function_context:
                response_key = "medications"
            elif "surgeries" in self.current_function_context:
                response_key = "surgeries"
            elif "allergies" in self.current_function_context:
                response_key = "allergies"
            elif "pain" in self.current_function_context and "scale" not in self.current_function_context:
                response_key = "pain"
            elif "scale" in self.current_function_context:
                response_key = "pain_scale"
            elif "worse" in self.current_function_context:
                response_key = "worse"
            elif "activities" in self.current_function_context:
                response_key = "activities"
            elif "previous" in self.current_function_context:
                response_key = "previous"
            elif "goals" in self.current_function_context:
                response_key = "goals"
            else:
                response_key = "name"  # Default fallback

            response = simulated_responses.get(response_key, "Yes")

        return response

    def _llm_interact(self, prompt, patient_context=None, system_role=None):
        """Interact with local Ollama LLM to generate responses"""
        try:
            # Default system role for physiotherapy assistant
            if system_role is None:
                system_role = """
                You are a professional physiotherapy assistant helping to gather patient information.
                Keep your responses concise and focused on physiotherapy assessment.
                Ask one question at a time and wait for a response.
                Format your responses to be spoken by a NAO robot.
                """

            # Prepare messages with context
            messages = []

            # Add system role
            if system_role:
                messages.append({"role": "system", "content": system_role})

            # Add patient context if available
            if patient_context:
                messages.append({"role": "system", "content": "Patient context: " + json.dumps(patient_context)})

            # Add the current prompt
            messages.append({"role": "user", "content": prompt})

            # Prepare the request payload for Ollama
            payload = {
                "model": self.ollama_model,
                "messages": messages,
                "stream": False
            }

            # Send request to Ollama
            response = requests.post(
                self.ollama_url + "/api/chat",
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload)
            )

            if response.status_code == 200:
                response_data = response.json()
                return response_data["message"]["content"]
            else:
                print("Error with Ollama LLM service: " + str(response.status_code))
                print(response.text)
                return "I'm experiencing a technical issue with my language model. Let me notify the physiotherapist."

        except Exception as e:
            print("Error with Ollama LLM service: " + str(e))
            # Provide a simple fallback response
            if "pain" in prompt.lower():
                return "I understand you're experiencing pain. Could you tell me more about where it hurts and what makes it worse?"
            elif "medication" in prompt.lower():
                return "Thank you for sharing about your medication. It's important for us to know this for your treatment plan."
            elif "exercise" in prompt.lower():
                return "Exercises are an important part of physiotherapy. We'll make sure to develop a suitable program for you."
            else:
                return "Thank you for sharing that information. It will help us provide better care for you."

    def greet_patient(self):
        """Greet the patient and introduce NAO as a physiotherapy assistant"""
        # Wave gesture
        self.motion.setAngles("RShoulderPitch", 0.5, 0.2)
        self.motion.setAngles("RShoulderRoll", -0.3, 0.2)
        self.motion.setAngles("RElbowRoll", 1.0, 0.2)
        self.motion.setAngles("RElbowYaw", 1.3, 0.2)
        self.motion.setAngles("RWristYaw", 0.0, 0.2)
        self.motion.setAngles("RHand", 0.8, 0.2)

        time.sleep(0.5)

        # Wave hand
        for _ in range(2):
            self.motion.setAngles("RElbowRoll", 0.8, 0.2)
            time.sleep(0.4)
            self.motion.setAngles("RElbowRoll", 1.0, 0.2)
            time.sleep(0.4)

        # Reset arm position
        self.motion.setAngles("RShoulderPitch", 1.4, 0.2)
        self.motion.setAngles("RShoulderRoll", -0.1, 0.2)

        # Greeting speech
        greeting = """
        Hello! I'm NAO, your physiotherapy assistant today. 
        I'll be helping to collect some information before your session with the physiotherapist.
        I'll ask you a few questions about your health and the reason for your visit today.
        You can answer naturally, and I'll guide you through the process.
        For best results, please speak clearly and directly toward me.
        """

        self._speak(greeting)

    def collect_personal_info(self):
        """Collect basic personal information from the patient"""
        self._speak("Let's start with some basic information about you.")

        # For each question, store context to help with simulated responses

        # Name
        self.current_function_context = "name"
        self._speak("What is your full name?")
        name = self._listen(15.0)
        if name:
            self.current_patient["personal_info"]["name"] = name

        # Age
        self.current_function_context = "age"
        if name and ' ' in name:
            first_name = name.split()[0]
        else:
            first_name = "there"
        self._speak("Thank you, " + first_name + ". What is your age?")
        age = self._listen(10.0)
        if age:
            self.current_patient["personal_info"]["age"] = age

        # Contact information
        self.current_function_context = "phone"
        self._speak("What is the best phone number to reach you?")
        phone = self._listen(15.0)
        if phone:
            self.current_patient["personal_info"]["phone"] = phone

        # Emergency contact
        self.current_function_context = "emergency"
        self._speak("In case of emergency, who should we contact and what is their relationship to you?")
        emergency_contact = self._listen(15.0)
        if emergency_contact:
            self.current_patient["personal_info"]["emergency_contact"] = emergency_contact

        # Add timestamp - strftime in Python 2.7
        self.current_patient["personal_info"]["registration_date"] = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S")

        # Confirmation
        if name and ' ' in name:
            self._speak("Thank you for providing your personal information, " + name.split()[0] + ".")
        else:
            self._speak("Thank you for providing your personal information.")

    def conduct_medical_history(self):
        """Use LLM to conduct a medical history interview"""
        self._speak("Now, I'd like to ask about your medical history. This helps us provide the best care for you.")

        # General health questions
        questions = [
            "Do you have any ongoing medical conditions I should be aware of?",
            "Are you currently taking any medications? If so, what are they?",
            "Have you had any surgeries or major injuries in the past?",
            "Do you have any allergies to medications or other substances?"
        ]

        # Context identifiers for simulated responses
        contexts = ["medical condition", "medication", "surgeries", "allergies"]

        for i, question in enumerate(questions):
            self.current_function_context = contexts[i]
            self._speak(question)
            response = self._listen(15.0)
            if response:
                # Use LLM to interpret and categorize the response
                interpretation = self._llm_interact(
                    "Interpret this patient response to '" + question + "': " + response,
                    system_role="Summarize the patient's response concisely and extract key medical information."
                )

                # Store both raw response and interpretation
                # Python 2.7 compatible string handling for dict key creation
                key = question.lower().replace("?", "").replace(" ", "_")[:30]
                self.current_patient["medical_history"][key] = {
                    "question": question,
                    "response": response,
                    "interpretation": interpretation
                }

        # Confirmation
        self._speak(
            "Thank you for sharing your medical history. This information will help us provide appropriate care.")

    def physiotherapy_assessment(self):
        """Conduct a physiotherapy-specific assessment"""
        self._speak("Now, let's talk specifically about what brings you in for physiotherapy today.")

        # Dynamically generate questions using LLM
        #assessment_prompt = """
        #Based on the patient's information so far: %s,
        #generate 5 specific physiotherapy assessment questions that would be most relevant.
        #Focus on pain location, movement limitations, daily activities affected, and treatment history.
        #Format as a JSON list of questions only.
        #""" % json.dumps(self.current_patient)

        assessment_prompt = """
        generate 5 specific physiotherapy assessment questions
        """



        questions_json = self._llm_interact(
            assessment_prompt,
            system_role="You are a physiotherapy assistant generating assessment questions."
        )

        try:
            # Try to parse the response as JSON
            questions = json.loads(questions_json)
        except:
            # Fallback questions if JSON parsing fails
            questions = [
                "Can you describe where you're experiencing pain or discomfort?",
                "On a scale of 0-10, how would you rate your pain, with 10 being the most severe?",
                "What movements or activities make your symptoms worse?",
                "What daily activities are difficult for you because of this issue?",
                "Have you had physiotherapy for this condition before? If so, what worked or didn't work?"
            ]

        # Context identifiers for simulated responses
        contexts = ["pain", "pain scale", "worse", "activities", "previous"]

        for i, question in enumerate(questions):
            self.current_function_context = contexts[
                i % len(contexts)]  # Use modulo in case we have more than 5 questions
            self._speak(question)
            response = self._listen(5.0)
            if response:
                # Generate a summary of the response
                summary = self._llm_interact(
                    "Summarize this physiotherapy assessment response concisely: " + response,
                    system_role="Extract key physiotherapy assessment information."
                )
                #self._speak(summary)
                # Store the information
                key = question.lower().replace("?", "").replace(" ", "_")[:30]
                self.current_patient["physiotherapy_assessment"][key] = {
                    "question": question,
                    "response": response,
                    "summary": summary
                }

        # Final question about goals
        self.current_function_context = "goals"
        self._speak("What are your goals for physiotherapy? What would you like to be able to do when you recover?")
        goals = self._listen(15.0)
        if goals:
            self.current_patient["physiotherapy_assessment"]["goals"] = goals

    def save_patient_profile(self):
        """Save the patient profile to a JSON file"""
        if not self.current_patient["personal_info"].get("name"):
            self._speak("I don't have enough information to save a profile. Let's try again.")
            return False

        # Create a filename based on patient name and date
        name = self.current_patient["personal_info"]["name"]
        safe_name = name.lower().replace(" ", "_")
        date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.patients_dir, safe_name + "_" + date + ".json")

        # Save the profile - Python 2.7 file handling
        try:
            with open(filename, 'w') as f:
                json.dump(self.current_patient, f, indent=4)
            return True
        except Exception as e:
            print("Error saving patient profile: " + str(e))
            return False

    def generate_summary(self):
        """Generate a summary of the patient assessment"""
        summary_prompt = """
        Create a concise summary of this patient's physiotherapy assessment based on:
        %s

        Include:
        1. Key symptoms and affected areas
        2. Relevant medical history
        3. Functional limitations
        4. Preliminary recommendations
        """ % json.dumps(self.current_patient)

        summary = self._llm_interact(
            summary_prompt,
            system_role="You are a physiotherapy assistant creating a patient summary for the physiotherapist."
        )

        return summary

    def conclude_assessment(self):
        """Conclude the assessment and inform the patient of next steps"""
        # Save the profile
        saved = self.save_patient_profile()

        if saved:
            # Generate a summary
            summary = self.generate_summary()
            self.current_patient["assessment_summary"] = summary

            # Update the saved file with the summary
            self.save_patient_profile()

            # Inform the patient
            conclusion = """
            Thank you for providing all this information. I've recorded your details for the physiotherapist.
            The physiotherapist will review this information before your session.
            They'll develop a personalized treatment plan based on your needs and goals.
            Is there anything else you'd like to share before we finish?
            """

            self._speak(conclusion)
            #self.current_function_context = "final comments"
            #final_comments = self._listen(15.0)
            #if final_comments:
            #    self.current_patient["final_comments"] = final_comments
            #    self.save_patient_profile()

            # Final goodbye
            self._speak("The physiotherapist will be with you shortly. I hope you have a productive session today ThankYou!")

            # Wave goodbye
            self.motion.setAngles("RShoulderPitch", 0.5, 0.2)
            self.motion.setAngles("RShoulderRoll", -0.3, 0.2)
            self.motion.setAngles("RWristYaw", 0.0, 0.2)
            self.motion.setAngles("RHand", 0.8, 0.2)

            # Wave hand
            for _ in range(2):
                self.motion.setAngles("RElbowRoll", 0.8, 0.2)
                time.sleep(0.4)
                self.motion.setAngles("RElbowRoll", 1.0, 0.2)
                time.sleep(0.4)

            # Reset to a neutral posture
            self.posture.goToPosture("Stand", 0.8)
        else:
            self._speak("I'm having trouble saving your information. Let me call the physiotherapist to assist you.")

    def run_full_assessment(self):
        """Run the complete patient assessment workflow"""
        try:
            # Start the assessment
            self.greet_patient()
            time.sleep(1)

            # Collect information
            self.collect_personal_info()
            time.sleep(1)

            self.conduct_medical_history()
            time.sleep(1)

            self.physiotherapy_assessment()
            time.sleep(1)

            # Conclude
            self.conclude_assessment()

            return True
        except Exception as e:
            print("Error during assessment: " + str(e))
            self._speak("I'm experiencing a technical issue. Let me notify the physiotherapist.")
            return False




if __name__ == "__main__":
    # Configuration
    ROBOT_IP = "172.18.16.54"  # Replace with your NAO's IP
    OLLAMA_URL = "http://localhost:11434"  # Replace with your Ollama server URL if different

    # Create the assistant
    assistant = PhysiotherapyAssistant(ROBOT_IP, ollama_url=OLLAMA_URL)
    # Run the assessment
    assistant.run_full_assessment()

