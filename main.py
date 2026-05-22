from flask import Flask, render_template, request, jsonify
import os
from datetime import datetime
import base64
import requests

# ===================== FIREBASE =====================
import firebase_admin
from firebase_admin import credentials, firestore, storage

# ===================== APP =====================
app = Flask(__name__, template_folder='templates')

# ===================== FIREBASE CONFIG =====================

# coloque o nome do seu arquivo json aqui
cred = credentials.Certificate("firebase-key.json")

firebase_admin.initialize_app(cred, {
    'storageBucket': 'SEU-PROJETO.appspot.com'
})

db = firestore.client()
bucket = storage.bucket()

# ===================== API LOCATION =====================
LOCATIONIQ_API_KEY = 'SUA_API_KEY'

# ===================== FUNÇÃO ENDEREÇO =====================
def obter_endereco(latitude, longitude):
    print(f"\n🔍 Buscando endereço: {latitude}, {longitude}")

    try:
        url = "https://us1.locationiq.com/v1/reverse"

        params = {
            'key': LOCATIONIQ_API_KEY,
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'accept-language': 'pt',
            'addressdetails': 1,
            'zoom': 18
        }

        response = requests.get(url, params=params, timeout=10)

        print(f"Status LocationIQ: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            endereco = data.get(
                'display_name',
                'Endereço não encontrado'
            )

            return {
                "endereco_completo": endereco,
                "fonte": "LocationIQ"
            }

    except Exception as e:
        print("❌ Erro LocationIQ:", e)

    return {
        "endereco_completo": "Não foi possível obter o endereço",
        "fonte": "Falha"
    }

# ===================== ROTAS =====================
@app.route('/')
def index():
    return render_template('index.html')

# ===================== REGISTRO =====================
@app.route('/registrar', methods=['POST'])
def registrar():

    try:
        print("📥 Requisição recebida")

        data = request.get_json(silent=True)

        if data is None:
            return jsonify({
                "erro": "JSON inválido"
            }), 400

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        foto_base64 = data.get('foto')

        print(
            f"📍 Lat: {latitude} | Lon: {longitude}"
        )

        # ===================== VALIDAÇÃO =====================

        if not latitude or not longitude or not foto_base64:
            return jsonify({
                "erro": "Latitude, longitude ou foto ausentes"
            }), 400

        # ===================== ENDEREÇO =====================

        endereco_info = obter_endereco(latitude, longitude)

        # ===================== FOTO BASE64 =====================

        try:

            if ',' in foto_base64:
                header, img_data = foto_base64.split(',', 1)
            else:
                img_data = foto_base64

            foto_bytes = base64.b64decode(img_data)

        except Exception as e:

            print("❌ Erro Base64:", e)

            return jsonify({
                "erro": "Imagem inválida"
            }), 400

        # ===================== NOME FOTO =====================

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"registro_{timestamp}.jpg"

        # ===================== UPLOAD FIREBASE STORAGE =====================

        blob = bucket.blob(f"uploads/{filename}")

        blob.upload_from_string(
            foto_bytes,
            content_type='image/jpeg'
        )

        # deixa público
        blob.make_public()

        foto_url = blob.public_url

        print("✅ Foto enviada:", foto_url)

        # ===================== REGISTRO FIRESTORE =====================

        registro = {
            "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "latitude": float(latitude),
            "longitude": float(longitude),
            "endereco": endereco_info.get("endereco_completo"),
            "fonte_endereco": endereco_info.get("fonte"),
            "foto": foto_url
        }

        db.collection('registros').add(registro)

        print("✅ Registro salvo no Firestore")

        # ===================== RESPOSTA =====================

        return jsonify({
            "mensagem": "Registro realizado com sucesso!",
            "foto": foto_url,
            "endereco": endereco_info.get("endereco_completo"),
            "fonte": endereco_info.get("fonte")
        })

    except Exception as e:

        print("❌ ERRO GERAL:", str(e))

        import traceback
        traceback.print_exc()

        return jsonify({
            "erro": str(e)
        }), 500

# ===================== START =====================
if __name__ == '__main__':

    print("🚀 Servidor iniciado")

    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    )
