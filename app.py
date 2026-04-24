from flask import Flask, request, send_file, redirect, session
from PIL import Image
from PyPDF2 import PdfMerger
import os
import uuid
import threading
import time

app = Flask(__name__)
app.secret_key = "chave_super_secreta_123"

# Segurança de sessão
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False  # mude para True quando estiver online (HTTPS)
)

# Limite de upload
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

BASE_UPLOAD = "uploads"
os.makedirs(BASE_UPLOAD, exist_ok=True)

# -------- LIMPEZA --------
def limpar_arquivos(pasta):
    time.sleep(5)
    try:
        for f in os.listdir(pasta):
            os.remove(os.path.join(pasta, f))
        os.rmdir(pasta)
    except:
        pass

# -------- LOGIN --------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        senha = request.form.get("senha")

        if senha == "Fantoni123x@@":
            session["logado"] = True
            session["user_id"] = str(uuid.uuid4())
            return redirect("/")
        else:
            return "Senha incorreta"

    return '''
    <h2>🔐 Login</h2>
    <form method="POST">
        <input type="password" name="senha" placeholder="Senha">
        <button type="submit">Entrar</button>
    </form>
    '''

# -------- PROTEÇÃO --------
@app.before_request
def proteger():
    rotas_livres = ["/login"]

    if request.path not in rotas_livres:
        if not session.get("logado"):
            return redirect("/login")

# -------- HOME --------
@app.route("/")
def home():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Juntar PDFs</title>
    <style>
        body { font-family: Arial; background: #f4f6f9; text-align: center; padding: 50px; }
        .box { background: white; padding: 30px; border-radius: 10px; width: 400px; margin: auto; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .drop-area { border: 2px dashed #007bff; padding: 30px; cursor: pointer; margin-bottom: 20px; border-radius: 10px; }
        .drop-area:hover { background: #f0f8ff; }
        input[type="file"] { display: none; }
        button { background: #007bff; color: white; border: none; padding: 12px; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }

        /* NOVO ESTILO DA LISTA */
        #file-list {
            list-style: none;
            padding: 0;
            margin-top: 20px;
        }

        #file-list li {
            background: #f8f9fa;
            margin: 5px 0;
            padding: 10px;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        #file-list button {
            margin-left: 5px;
            padding: 5px 8px;
            font-size: 12px;
        }
    </style>
</head>
<body>

<div class="box">
    <h2>📄 Juntar arquivos em PDF</h2>

    <form>
       <form>
    <label class="drop-area" id="drop-area">
        Arraste arquivos aqui ou clique
        <input type="file" id="fileElem" multiple required>
    </label>

    <p id="file-count">Nenhum arquivo selecionado</p>

    <ul id="file-list"></ul>

    <br>
    <button type="submit">Gerar PDF</button>
</form>
</div>

<script>
let arquivos = [];

const dropArea = document.getElementById("drop-area");
const fileInput = document.getElementById("fileElem");
const fileList = document.getElementById("file-list");
const fileCount = document.getElementById("file-count");

// Clique abre seletor
dropArea.addEventListener("click", () => fileInput.click());

// Arrastar arquivos
dropArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropArea.style.background = "#e0f0ff";
});

dropArea.addEventListener("dragleave", () => {
    dropArea.style.background = "";
});

dropArea.addEventListener("drop", (e) => {
    e.preventDefault();
    arquivos = Array.from(e.dataTransfer.files);
    renderLista();
});

// Seleção normal
fileInput.addEventListener("change", (e) => {
   arquivos = arquivos.concat(Array.from(e.target.files));
    renderLista();
    fileInput.value = "";
});

// Mostrar lista
function renderLista() {
    fileList.innerHTML = "";

    fileCount.textContent = arquivos.length + " arquivo(s) selecionado(s)";

    arquivos.forEach((file, index) => {
        const li = document.createElement("li");

        let preview = "";

        // Preview imagem
        if (file.type.startsWith("image/")) {
            const url = URL.createObjectURL(file);
            preview = `<img src="${url}" width="80">`;
        }

        // Preview PDF
        else if (file.type === "application/pdf") {
            const url = URL.createObjectURL(file);
            preview = `<iframe src="${url}" width="80" height="100"></iframe>`;
        }

        li.innerHTML = `
            <div>
                <strong>${file.name}</strong><br>
                ${preview}
            </div>
            <div>
                <button onclick="mover(${index}, -1)">⬆️</button>
                <button onclick="mover(${index}, 1)">⬇️</button>
                <button onclick="remover(${index})">❌</button>
            </div>
        `;

        fileList.appendChild(li);
    });
}

// Mover arquivos
function mover(index, direcao) {
    const novoIndex = index + direcao;

    if (novoIndex < 0 || novoIndex >= arquivos.length) return;

    [arquivos[index], arquivos[novoIndex]] =
    [arquivos[novoIndex], arquivos[index]];

    renderLista();
}
function remover(index) {
    arquivos.splice(index, 1);
    renderLista();
}
// Enviar na ordem correta
document.querySelector("form").addEventListener("submit", function(e) {
console.log("FORMULARIO ENVIADO");
    e.preventDefault();

    const formData = new FormData();

    arquivos.forEach(file => {
        formData.append("files", file);
    });

    fetch("/merge", {
        method: "POST",
        body: formData
    })
    .then(res => res.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "resultado.pdf";
        a.click();
    });
});
</script>

</body>
</html>
'''

# -------- MERGE --------
@app.route("/merge", methods=["POST"])
def merge():
    files = request.files.getlist("files")

    if len(files) > 10:
        return "Máximo de 10 arquivos permitido", 400

    user_id = session.get("user_id")
    user_folder = os.path.join(BASE_UPLOAD, user_id)
    os.makedirs(user_folder, exist_ok=True)

    pdfs = []
    extensoes = (".jpg", ".jpeg", ".png", ".pdf")

    for file in files:
        filename = str(uuid.uuid4()) + "_" + file.filename
        path = os.path.join(user_folder, filename)
        file.save(path)

        if not filename.lower().endswith(extensoes):
            return "Arquivo inválido", 400

        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            img = Image.open(path).convert("RGB")
            pdf_path = path + ".pdf"
            img.save(pdf_path)
            pdfs.append(pdf_path)
        else:
            pdfs.append(path)

    merger = PdfMerger()

    for pdf in pdfs:
        merger.append(pdf)

    output = os.path.join(user_folder, "resultado.pdf")
    merger.write(output)
    merger.close()

    # limpeza em segundo plano
    threading.Thread(target=limpar_arquivos, args=(user_folder,)).start()

    return send_file(output, as_attachment=True)

# -------- RUN --------
if __name__ == "__main__":
    app.run(debug=True)
