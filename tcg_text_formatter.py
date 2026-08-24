# tcg_text_formatter.py - CORRETTO
import re

def genera_qualificatore(finitura: str, rarita: str) -> str:
    """Genera il qualificatore della carta (es: 'Reverse Holo Rare')"""
    rarita_valida = rarita not in ["Comune", "Non Comune", "NONE", "", None]
    finitura_valida = finitura not in ["base", "NONE", "", None]
    
    if finitura_valida and rarita_valida:
        if finitura.lower() == rarita.lower():
            return finitura
        return f"{finitura} {rarita}"
    elif finitura_valida:
        return finitura
    elif rarita_valida:
        return rarita
    return ""

def pulisci_tag(testo: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', testo)

def genera_hashtags(nome: str, set_codice: str, lingua: str, rarita: str, finitura: str) -> str:
    tags = [
        "#PokemonTCG",
        "#Pokemon",
        f"#{pulisci_tag(nome)}",
        f"#Pokemon{lingua.capitalize()}",
        "#CartaPokemon",
        "#CartePokemon",
        f"#{set_codice}" if set_codice != "UNK" else "",
        f"#{pulisci_tag(rarita)}" if rarita not in ["Comune", "NONE"] else "",
        "#Reverse" if finitura and "Reverse" in finitura else ""
    ]
    tags = [t for t in tags if t]
    seen = set()
    return " ".join([x for x in tags if not (x in seen or seen.add(x))])

def componi_annuncio_pokemon(
    nome: str,
    numero: str,
    set_nome: str,
    set_codice: str,
    lingua_codice: str = "ITA",
    rarita: str = "Comune",
    finitura: str = "base",
    categoria: str = "normale",
    condizione: str = "Ottime Condizioni",
    tipo_energia: str = ""
) -> dict:
    """Componi un annuncio Pokémon completo e ben formattato"""
    
    qualificatore = genera_qualificatore(finitura, rarita)
    lingua_cap = lingua_codice.upper()
    
    # Titolo
    if qualificatore:
        title = f"{nome} {numero} {qualificatore} {lingua_cap}"
    else:
        title = f"{nome} {numero} Pokémon TCG {lingua_cap}"
    title = title[:100].strip()
    
    # Espansione
    espansione_str = f"{set_nome} ({set_codice})" if set_codice else set_nome
    
    # Prima riga
    if qualificatore:
        riga_1 = f"🎴 Vendo carta Pokémon TCG {nome} {qualificatore} {numero} in {lingua_codice.lower()} originale."
    else:
        riga_1 = f"🎴 Vendo carta Pokémon TCG {nome} {numero} in {lingua_codice.lower()} originale."
    
    # Descrizione tipo
    if qualificatore:
        frase_tipo = f"Carta Pokémon singola {qualificatore}"
    else:
        frase_tipo = "Carta Pokémon singola"
    
    # Dettagli
    dettagli = [
        f"Nome: {nome}",
        f"Numero: {numero}",
        f"Espansione: {espansione_str}",
        f"Lingua: {lingua_codice.upper()}",
        f"Condizioni: {condizione}"
    ]
    if rarita not in ["Comune", "NONE", "", None]:
        dettagli.insert(3, f"Rarità: {rarita}")
    if finitura not in ["base", "NONE", "", None]:
        dettagli.insert(4, f"Finitura: {finitura}")
    
    dettagli_testo = "\n".join(dettagli)
    hashtags = genera_hashtags(nome, set_codice, lingua_codice, rarita, finitura)
    
    description = (
        f"{riga_1}\n"
        f"✨ {frase_tipo} dell'espansione {espansione_str}, ideale per collezionisti e giocatori Pokémon TCG.\n\n"
        f"📋 Dettagli:\n"
        f"{dettagli_testo}\n\n"
        f"📸 Riceverai esattamente ciò che vedi in foto. Le foto sono parte integrante della descrizione.\n"
        f"📦 La carta verrà spedita protetta con sleeve e/o supporto rigido per garantirne la massima sicurezza durante il trasporto.\n"
        f"🚚 Spedizione generalmente effettuata entro 24h lavorative.\n"
        f"🛒 Consulta il mio armadio per altre carte Pokémon e annunci simili.\n"
        f"💥 Acquistando più articoli puoi creare un set e ottenere sconti dedicati.\n\n"
        f"{hashtags}"
    )
    
    return {
        "title": title,
        "description": description[:2000]
    }

if __name__ == "__main__":
    res = componi_annuncio_pokemon("Pikachu", "001/100", "Surging Sparks", "SSP", "ITA", "Holo Rare", "Reverse")
    print(res["title"])
    print(res["description"])