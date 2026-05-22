from flask import Flask, render_template, request, jsonify
import os
from datetime import datetime
import base64
import requests
from supabase import create_client

app = Flask(__name__, template_folder='templates')

# ===================== SUPABASE =====================
SUPABASE_URL = "SUA_SUPABASE_URL"
SUPABASE_KEY = "SUA_SUPABASE_KEY"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===================== CONFIG =====================
LOCATIONIQ_API_KEY = "SUA_LOCATIONIQ_KEY"

# ===================== FUNÇÕES =====================
def obter_endereco(latitude, longitude):
    print(f"\n🔍 Tentando obter endereço para: {latitude}, {longitude}")

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

        print(f"LocationIQ Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            endereco = data.get('display_name', 'Não encontrado')

            print(f"✅ LocationIQ sucesso: {endereco[:120]}...")

            return {
                "endereco_completo": endereco,
                "fonte": "LocationIQ"
            }

    except Exception as e:
        print(f"❌ Erro LocationIQ: {e}")

    return {
        "endereco_completo": "Não foi possível obter o endereço",
        "fonte": "Falha"
    }

# ===================== ROTAS =====================
@app.route('/')
def index():
    return render_template('index.html')

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

        if not latitude or not longitude or not foto_base64:
            return jsonify({
                "erro": "Faltam dados"
            }), 400

        # ===================== ENDEREÇO =====================
        endereco_info = obter_endereco(latitude, longitude)

        # ===================== FOTO =====================
        try:

            if ',' in foto_base64:
                _, img_data = foto_base64.split(',', 1)
            else:
                img_data = foto_base64

            foto_bytes = base64.b64decode(img_data)

        except Exception as e:
            print("❌ Erro ao decodificar imagem:", e)

            return jsonify({
                "erro": "Imagem inválida"
            }), 400

        # ===================== NOME DO ARQUIVO =====================
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"registro_{timestamp}.jpg"

        # ===================== UPLOAD SUPABASE =====================
        upload_response = supabase.storage.from_("fotos").upload(
            path=filename,
            file=foto_bytes,
            file_options={
                "content-type": "image/jpeg"
            }
        )

        print("📤 Upload Supabase:", upload_response)

        # ===================== URL PÚBLICA =====================
        foto_url = supabase.storage.from_("fotos").get_public_url(filename)

        print("🖼️ URL Foto:", foto_url)

        # ===================== SALVAR NO BANCO =====================
        registro = {
            "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "latitude": float(latitude),
            "longitude": float(longitude),
            "endereco": endereco_info.get("endereco_completo"),
            "fonte_endereco": endereco_info.get("fonte"),
            "foto_url": foto_url
        }

        response = supabase.table("registros").insert(registro).execute()

        print("💾 Registro salvo:", response)

        return jsonify({
            "mensagem": "Registro salvo com sucesso!",
            "foto_url": foto_url,
            "endereco": endereco_info.get("endereco_completo")
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

    print("🚀 Servidor rodando")

    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    )
