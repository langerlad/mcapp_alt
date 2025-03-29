# client_code/Vypocty.py - modul pro sdílené výpočty

import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


def normalizuj_matici_minmax(matice, typy_kriterii, varianty, kriteria):
    """
    Provede min-max normalizaci hodnot matice.
    
    Args:
        matice: 2D list s hodnotami [varianty][kriteria]
        typy_kriterii: List typů kritérií ("max" nebo "min")
        varianty: List názvů variant
        kriteria: List názvů kritérií
    
    Returns:
        dict: Slovník obsahující normalizovanou matici a metadata
    """
    norm_matice = []
    for i in range(len(matice)):
        norm_radek = []
        for j in range(len(matice[0])):
            sloupec = [row[j] for row in matice]
            min_val = min(sloupec)
            max_val = max(sloupec)
            
            if max_val == min_val:
                norm_hodnota = 1.0  # Všechny hodnoty jsou stejné
            else:
                # Pro MIN kritéria obrátíme normalizaci
                if typy_kriterii[j].lower() in ("min", "cost"):
                    norm_hodnota = (max_val - matice[i][j]) / (max_val - min_val)
                else:
                    norm_hodnota = (matice[i][j] - min_val) / (max_val - min_val)
                
            norm_radek.append(norm_hodnota)
        norm_matice.append(norm_radek)
    
    return {
        'nazvy_variant': varianty,
        'nazvy_kriterii': kriteria,
        'normalizovana_matice': norm_matice
    }

def vytvor_hodnoty_matici(analyza_data):
    """
    Vytvoří matici s hodnotami z dat analýzy.
    
    Args:
        analyza_data: Slovník s daty analýzy
    
    Returns:
        tuple: (matice, typy_kriterii, varianty, kriteria)
    """
    varianty = [v['nazev_varianty'] for v in analyza_data['varianty']]
    kriteria = [k['nazev_kriteria'] for k in analyza_data['kriteria']]
    typy_kriterii = [k['typ'] for k in analyza_data['kriteria']]
    
    # Vytvoření původní matice
    matice = []
    for var in analyza_data['varianty']:
        radek = []
        for krit in analyza_data['kriteria']:
            klic = f"{var['nazev_varianty']}_{krit['nazev_kriteria']}"
            hodnota = float(analyza_data['hodnoty']['matice_hodnoty'].get(klic, 0))
            radek.append(hodnota)
        matice.append(radek)
    
    return matice, typy_kriterii, varianty, kriteria

def vypocitej_vazene_hodnoty(matice, vahy):
    """
    Vypočítá vážené hodnoty (váhy × normalizované hodnoty).
    
    Args:
        matice: 2D list normalizovaných hodnot
        vahy: List vah kritérií
    
    Returns:
        2D list vážených hodnot
    """
    vazene_matice = []
    for radek in matice:
        vazene_radek = [hodnota * vahy[i] for i, hodnota in enumerate(radek)]
        vazene_matice.append(vazene_radek)
    return vazene_matice

# Specifické funkce pro jednotlivé metody

def wsm_vypocet(norm_matice, vahy, varianty):
    """
    Provede výpočet metodou WSM (Weighted Sum Model).
    
    Args:
        norm_matice: 2D list normalizovaných hodnot
        vahy: List vah kritérií
        varianty: List názvů variant
    
    Returns:
        dict: Výsledky analýzy metodou WSM
    """
    vazene_hodnoty = vypocitej_vazene_hodnoty(norm_matice, vahy)
    
    # Sečtení řádků (variant) pro získání skóre
    skore = []
    for i, vazene_radek in enumerate(vazene_hodnoty):
        skore.append((varianty[i], sum(vazene_radek)))
    
    # Seřazení podle skóre sestupně
    serazene = sorted(skore, key=lambda x: x[1], reverse=True)
    
    # Vytvoření seznamu výsledků s pořadím
    results = []
    for poradi, (varianta, hodnota) in enumerate(serazene, 1):
        results.append((varianta, poradi, hodnota))
    
    return {
        'results': results,
        'nejlepsi_varianta': results[0][0],
        'nejlepsi_skore': results[0][2],
        'nejhorsi_varianta': results[-1][0],
        'nejhorsi_skore': results[-1][2],
        'rozdil_skore': results[0][2] - results[-1][2]
    }

def priprav_data_z_json(analyza_data):
    """
    Připraví data z JSON struktury pro výpočty.
    
    Args:
        analyza_data: Slovník s daty analýzy v novém formátu
        
    Returns:
        tuple: (matice, typy_kriterii, varianty, kriteria, vahy)
    """
    try:
        # Získání seznamu kritérií a jejich typů
        kriteria_dict = analyza_data.get('kriteria', {})
        kriteria = list(kriteria_dict.keys())
        typy_kriterii = [kriteria_dict[k]['typ'] for k in kriteria]
        vahy = [float(kriteria_dict[k]['vaha']) for k in kriteria]
        
        # Získání seznamu variant
        varianty_dict = analyza_data.get('varianty', {})
        varianty = list(varianty_dict.keys())
        
        # Vytvoření matice hodnot
        matice = []
        for var_nazev in varianty:
            var_data = varianty_dict[var_nazev]
            radek = []
            for krit_nazev in kriteria:
                # Získáme hodnotu pro kritérium, výchozí je 0 pokud chybí
                hodnota = 0
                if krit_nazev in var_data:
                    try:
                        hodnota = float(var_data[krit_nazev])
                    except (ValueError, TypeError):
                        hodnota = 0
                radek.append(hodnota)
            matice.append(radek)
            
        return matice, typy_kriterii, varianty, kriteria, vahy
        
    except Exception as e:
        raise ValueError(f"Chyba při přípravě dat pro výpočet: {str(e)}")

def vypocitej_analyzu_citlivosti(norm_matice, vahy, varianty, kriteria, vyber_kriteria=0, pocet_kroku=9):
    """
    Provede analýzu citlivosti změnou váhy vybraného kritéria.
    
    Args:
        norm_matice: 2D list normalizovaných hodnot
        vahy: List vah kritérií
        varianty: List názvů variant
        kriteria: List názvů kritérií
        vyber_kriteria: Index kritéria, jehož váha se bude měnit (výchozí je první kritérium)
        pocet_kroku: Počet kroků při změně váhy
        
    Returns:
        dict: Výsledky analýzy citlivosti
    """
    try:
        # Vytvoření rozsahu vah pro analýzu citlivosti
        vahy_rozsah = []
        for i in range(pocet_kroku):
            # Váha od 0.1 do 0.9
            vahy_rozsah.append(0.1 + (0.8 * i / (pocet_kroku - 1)))
        
        citlivost_skore = []    # Bude obsahovat skóre pro každou kombinaci váhy a varianty
        citlivost_poradi = []   # Bude obsahovat pořadí pro každou kombinaci váhy a varianty
        
        # Pro každou váhu v rozsahu
        for vaha in vahy_rozsah:
            # Vytvoření nových vah
            nove_vahy = vahy.copy()
            nove_vahy[vyber_kriteria] = vaha
            
            # Přepočítání vah zbývajících kritérií proporcionálně
            zbyvajici_vaha = 1 - vaha
            
            suma_zbylych_vah = sum(nove_vahy) - nove_vahy[vyber_kriteria]
            if suma_zbylych_vah > 0:
                for i in range(len(nove_vahy)):
                    if i != vyber_kriteria:
                        nove_vahy[i] = (nove_vahy[i] / suma_zbylych_vah) * zbyvajici_vaha
            
            # Výpočet nových skóre
            skore_variant = []
            for i in range(len(varianty)):
                skore = 0
                for j in range(len(kriteria)):
                    skore += norm_matice[i][j] * nove_vahy[j]
                skore_variant.append(skore)
            
            # Určení pořadí variant pro tyto váhy
            serazene_indexy = sorted(range(len(skore_variant)), 
                                    key=lambda k: skore_variant[k], 
                                    reverse=True)
            poradi_variant = [0] * len(varianty)
            for poradi, idx in enumerate(serazene_indexy, 1):
                poradi_variant[idx] = poradi
            
            citlivost_skore.append(skore_variant)
            citlivost_poradi.append(poradi_variant)
        
        return {
            'vahy_rozsah': vahy_rozsah,
            'citlivost_skore': citlivost_skore,
            'citlivost_poradi': citlivost_poradi,
            'zvolene_kriterium': kriteria[vyber_kriteria],
            'zvolene_kriterium_index': vyber_kriteria
        }
    except Exception as e:
        raise ValueError(f"Chyba při výpočtu analýzy citlivosti: {str(e)}")

def topsis_vypocet(norm_matice, vahy, varianty, kriteria):
    """
    Vypočítá výsledky metodou TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution).
    
    Args:
        norm_matice: 2D list normalizovaných hodnot
        vahy: List vah kritérií
        varianty: List názvů variant
        kriteria: List názvů kritérií
    
    Returns:
        dict: Výsledky analýzy metodou TOPSIS
    """
    try:
        # Výpočet vážené normalizované matice
        vazena_matice = []
        for i in range(len(varianty)):
            radek = []
            for j in range(len(kriteria)):
                radek.append(norm_matice[i][j] * vahy[j])
            vazena_matice.append(radek)
        
        # Výpočet ideálního a anti-ideálního řešení
        ideal = []
        anti_ideal = []
        for j in range(len(kriteria)):
            sloupec = [vazena_matice[i][j] for i in range(len(varianty))]
            ideal.append(max(sloupec))
            anti_ideal.append(min(sloupec))
        
        # Výpočet vzdáleností od ideálního a anti-ideálního řešení
        dist_ideal = []
        dist_anti_ideal = []
        for i in range(len(varianty)):
            sum_ideal = 0
            sum_anti_ideal = 0
            for j in range(len(kriteria)):
                sum_ideal += (vazena_matice[i][j] - ideal[j]) ** 2
                sum_anti_ideal += (vazena_matice[i][j] - anti_ideal[j]) ** 2
            dist_ideal.append(sum_ideal ** 0.5)
            dist_anti_ideal.append(sum_anti_ideal ** 0.5)
        
        # Výpočet relativní blízkosti k ideálnímu řešení
        blízkost = []
        for i in range(len(varianty)):
            if dist_ideal[i] + dist_anti_ideal[i] == 0:
                blízkost.append(0)
            else:
                blízkost.append(dist_anti_ideal[i] / (dist_ideal[i] + dist_anti_ideal[i]))
        
        # Seřazení variant podle blízkosti (sestupně)
        skore = [(varianty[i], blízkost[i]) for i in range(len(varianty))]
        serazene = sorted(skore, key=lambda x: x[1], reverse=True)
        
        # Vytvoření seznamu výsledků s pořadím
        results = []
        for poradi, (varianta, hodnota) in enumerate(serazene, 1):
            results.append((varianta, poradi, hodnota))
        
        return {
            'results': results,
            'nejlepsi_varianta': results[0][0],
            'nejlepsi_skore': results[0][2],
            'nejhorsi_varianta': results[-1][0],
            'nejhorsi_skore': results[-1][2],
            'ideal': ideal,
            'anti_ideal': anti_ideal,
            'vazena_matice': vazena_matice
        }
    except Exception as e:
        raise ValueError(f"Chyba při výpočtu TOPSIS: {str(e)}")

def wpm_vypocet(matice, vahy, typy_kriterii, varianty, kriteria):
    """
    Vypočítá výsledky metodou WPM (Weighted Product Model).
    
    Args:
        matice: 2D list původních hodnot
        vahy: List vah kritérií
        typy_kriterii: List typů kritérií ("max" nebo "min")
        varianty: List názvů variant
        kriteria: List názvů kritérií
    
    Returns:
        dict: Výsledky analýzy metodou WPM
    """
    try:
        # Pro WPM používáme přímo původní hodnoty, nikoliv normalizované
        # Inicializace výsledných hodnot na 1 pro násobení
        skore = [1.0] * len(varianty)
        
        for i in range(len(varianty)):
            for j in range(len(kriteria)):
                hodnota = matice[i][j]
                
                # Kontrola, že hodnoty nejsou nulové nebo záporné
                if hodnota <= 0:
                    hodnota = 0.001  # Malá kladná hodnota
                
                # Pro minimalizační kritéria používáme 1/hodnota
                if typy_kriterii[j].lower() in ("min", "cost"):
                    hodnota = 1 / hodnota
                
                # Umocníme hodnotu na váhu a vynásobíme dosavadní skóre
                skore[i] *= hodnota ** vahy[j]
        
        # Seřazení variant podle skóre (sestupně)
        skore_varianty = [(varianty[i], skore[i]) for i in range(len(varianty))]
        serazene = sorted(skore_varianty, key=lambda x: x[1], reverse=True)
        
        # Vytvoření seznamu výsledků s pořadím
        results = []
        for poradi, (varianta, hodnota) in enumerate(serazene, 1):
            results.append((varianta, poradi, hodnota))
        
        return {
            'results': results,
            'nejlepsi_varianta': results[0][0],
            'nejlepsi_skore': results[0][2],
            'nejhorsi_varianta': results[-1][0],
            'nejhorsi_skore': results[-1][2],
            'rozdil_skore': results[0][2] - results[-1][2] if len(results) > 1 else 0
        }
    except Exception as e:
        raise ValueError(f"Chyba při výpočtu WPM: {str(e)}")