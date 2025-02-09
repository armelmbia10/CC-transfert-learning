import streamlit as st
from PIL import Image
import numpy as np
import tensorflow as tf
import replicate
import os 
import requests
# Charger votre modèle pré-entraîné
# Assurez-vous de remplacer 'votre_modele.h5' par le chemin de votre modèle
model = tf.keras.models.load_model('model.h5')

ICON_BLUE = "icone.png"
sidebar_logo = ICON_BLUE
main_body_logo = None

st.logo(sidebar_logo, icon_image=main_body_logo)
st.sidebar.markdown("Bienvenue sur Kidney App")

# Fonction pour prédire la classe d'une image
def predict_image(image):
    image = image.resize((224, 224))  # Redimensionner si nécessaire
    img_array = np.array(image) / 255.0  # Normaliser
    img_array = np.expand_dims(img_array, axis=0)  # Ajouter la dimension du lot
    predictions = model.predict(img_array)
    return np.argmax(predictions)

# Titre de l'application
st.title("Classification d'images de radios de reins")
st.image("kidney.webp",width=600)
st.markdown("""
    <style>
    body { background-color: blue; }
    .stApp {
        background-image: linear-gradient(to bottom, rgba(255,128,255,0.5), rgba(0,0,128,0.5)), url("https://images.radio-canada.ca/q_auto,w_960/v1/ici-premiere/16x9/sante-intelligence-artificielle-soins-technologie-environnement-vie-privee-mdr.jpg")
    }
        background-size: cover;
    }
    </style>
    """, unsafe_allow_html=True)

# Uploader une image
uploaded_file = st.file_uploader("Choisissez une image de radio de reins", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='Image téléchargée', use_container_width=True)

    # Prédiction
    if st.button("Classer l'image"):
        predictions = model.predict(np.expand_dims(np.array(image.resize((224, 224))) / 255.0, axis=0))
        class_index = np.argmax(predictions)
        # Map class_index to the corresponding label
        labels = ["Cyst", "Normal", "Stone","Tumor"]  # Replace with your actual class labels
        predicted_label = labels[class_index]
        st.write(f"Classe prédite : {predicted_label}")
        # Afficher les détails de la prédiction
        st.subheader("Détails de la prédiction")
        for i, label in enumerate(labels):
            st.write(f"{label}: {predictions[0][i]*100:.2f}%")


os.environ["REPLICATE_API_TOKEN"] = "r8_"
# Replicate Credentials
with st.sidebar:
    st.title('Chatbot de conseils de santé')
    if 'REPLICATE_API_TOKEN' in st.secrets:
        st.success('API key already provided!', icon='✅')
        replicate_api = st.secrets['REPLICATE_API_TOKEN']
    else:
        replicate_api = st.text_input('Enter Replicate API token:', type='password')
        if not (replicate_api.startswith('r8_') and len(replicate_api)==40):
            st.warning('Please enter your credentials!', icon='⚠')
        else:
            st.success('Proceed to entering your prompt message!', icon='👉')
    os.environ['REPLICATE_API_TOKEN'] = replicate_api
    with st.sidebar.expander("Models and parameters"):
        st.subheader('Models and parameters')
        selected_model = st.selectbox('Choose a Llama2 model', ['Llama2-7B', 'Llama2-13B'], key='selected_model')
        if selected_model == 'Llama2-7B':
            llm = 'a16z-infra/llama7b-v2-chat:4f0a4744c7295c024a1de15e1a63c880d3da035fa1f49bfd344fe076074c8eea'
        elif selected_model == 'Llama2-13B':
            llm = 'a16z-infra/llama13b-v2-chat:df7690f1994d94e96ad9d568eac121aecf50684a0b0963b25a41cc40061269e5'
        temperature = st.slider('temperature', min_value=0.01, max_value=5.0, value=0.1, step=0.01)
        top_p = st.slider('top_p', min_value=0.01, max_value=1.0, value=0.9, step=0.01)
        max_length = st.slider('max_length', min_value=32, max_value=128, value=120, step=8)
# Store LLM generated responses
if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "assistant", "content": "Posez une question au chatbot concernant la santé :"}]

# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

def clear_chat_history():
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]
st.sidebar.button('Clear Chat History', on_click=clear_chat_history)

# Function for generating LLaMA2 response. Refactored from https://github.com/a16z-infra/llama2-chatbot
def generate_llama2_response(prompt_input):
    string_dialogue = "You are a helpful assistant. You do not respond as 'User' or pretend to be 'User'. You only respond once as 'Assistant'."
    for dict_message in st.session_state.messages:
        if dict_message["role"] == "user":
            string_dialogue += "User: " + dict_message["content"] + "\n\n"
        else:
            string_dialogue += "Assistant: " + dict_message["content"] + "\n\n"
    output = replicate.run('a16z-infra/llama13b-v2-chat:df7690f1994d94e96ad9d568eac121aecf50684a0b0963b25a41cc40061269e5', 
                           input={"prompt": f"{string_dialogue} {prompt_input} Assistant: ",
                                  "temperature":temperature, "top_p":top_p, "max_length":max_length, "repetition_penalty":1})
    return output

# User-provided prompt
if prompt := st.chat_input(disabled=not replicate_api):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

# Generate a new response if last message is not from assistant
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = generate_llama2_response(prompt)
            placeholder = st.empty()
            full_response = ''
            for item in response:
                full_response += item
                placeholder.markdown(full_response)
            placeholder.markdown(full_response)
    message = {"role": "assistant", "content": full_response}
    st.session_state.messages.append(message)