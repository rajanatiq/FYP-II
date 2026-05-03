from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')  # ~80MB, fast

question = "what is machine learning in context of aritifical intelligence?"
voice_text = "is a subset of artifical intelligence"

q_embedding = model.encode(question)
v_embedding = model.encode(voice_text)

similarity = util.cos_sim(q_embedding, v_embedding) #type: ignore
print(f"Similarity: {similarity.item():.2f}")  # 0.0 to 1.0