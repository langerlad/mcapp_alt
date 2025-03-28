# -------------------------------------------------------
# Modul: Utils
# -------------------------------------------------------
from anvil import confirm

def zapsat_info(zprava):
    """
    Pomocná funkce pro konzolové výpisy info v klientském kódu.
    
    Args:
        zprava (str): Informační zpráva k vypsání
    """
    print(f"[INFO] {zprava}")

def zapsat_chybu(zprava):
    """
    Pomocná funkce pro konzolové výpisy chyb v klientském kódu.
    
    Args:
        zprava (str): Chybová zpráva k vypsání
    """
    print(f"[CHYBA] {zprava}")

def zobraz_potvrzovaci_dialog(zprava, ano_text="Ano", ne_text="Ne"):
    """
    Zobrazí potvrzovací dialog s vlastním textem tlačítek.
    
    Args:
        zprava (str): Text zprávy v dialogu
        ano_text (str): Text pro potvrzovací tlačítko
        ne_text (str): Text pro zamítací tlačítko
        
    Returns:
        bool: True pokud uživatel potvrdil, jinak False
    """
    return confirm(zprava, dismissible=True, 
                  buttons=[(ano_text, True), (ne_text, False)])

def normalizuj_desetinne_cislo(text):
    """
    Převede textový vstup na desetinné číslo.
    Nahradí čárku tečkou a ověří platnost formátu.
    
    Args:
        text (str): Textový vstup
        
    Returns:
        float: Normalizované číslo
        
    Raises:
        ValueError: Pokud vstup není platné číslo
    """
    if not text:
        raise ValueError("Hodnota je povinná")
        
    # Nahrazení čárky za tečku
    text = text.replace(',', '.')
    
    try:
        hodnota = float(text)
        return hodnota
    except ValueError:
        raise ValueError("Zadaná hodnota není platné číslo")