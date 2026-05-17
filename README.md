Säkerhetspipeline — examensarbete DT099G
Automatiserad säkerhetspipeline för statisk analys av AI-genererad Pythonkod. Kör Bandit, Semgrep, detect-secrets och pip-audit i sekvens.
Bygger på Kyi Thars ramverk (github.com/khukt/AI-generated-code-security-check) med modifieringar av författaren — främst en verktygsoberoende dedupliceringsfunktion för komplementaritetsanalys.
Köra
pip install -r requirements.txt
streamlit run app.py
