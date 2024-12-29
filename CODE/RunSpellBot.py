import pandas as pd
from qdrant_client import models, QdrantClient
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import pandas as pd
from flask import Flask, send_file, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(
    # This base_url points to the local Llamafile server running on port 8080
    base_url="http://127.0.0.1:8080/v1",
    api_key="sk-no-key-required"
)
@app.route('/')
def index():
    return send_file('index.html')
@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json['message']
        df = pd.read_csv('../DATA/SpellsTable.csv')
        #print(df.head())
        df = df[df['Name'].notna()] # remove any NaN values as it blows up serialization
        data = df.to_dict('records')

        encoder = SentenceTransformer('all-MiniLM-L6-v2') # Model to create embeddings
        # create the vector database client
        qdrant = QdrantClient(":memory:") # Create in-memory Qdrant instance
        # Create collection to store wines
        qdrant.create_collection(
            collection_name="spells",
            vectors_config=models.VectorParams(
                size=encoder.get_sentence_embedding_dimension(), # Vector size is defined by used model
                distance=models.Distance.COSINE
            )
        )
        # vectorize!
        qdrant.upload_points(
            collection_name="spells",
            points=[
            models.PointStruct(
                    id=idx,
                    vector=encoder.encode(doc["Description"]).tolist(),
                    payload=doc,
                ) for idx, doc in enumerate(data) # data is the variable holding all the wines
            ])
        search_results = qdrant.search(
            collection_name="spells",
            query_vector=encoder.encode(user_message).tolist(),
            limit=1
        )

        completion = client.chat.completions.create(
            model="LLaMA_CPP",
            messages=[
                {"role": "system", "content": "You are chatbot, an assistant to a spell caster. Your top priority is to help guide user into selecting which spell name to use and guide them with their requests."},
                {"role": "user", "content": f"{user_message}"},
                {"role": "assistant", "content": str(search_results)}
            ]
        )

        ai_response = completion.choices[0].message.content
        ai_response = ai_response.replace('</s>', '').strip()
        return jsonify({'response': ai_response})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'response': f"Sorry, there was an error processing your request: {str(e)}"}), 500
if __name__ == '__main__':

    app.run(debug=True)
