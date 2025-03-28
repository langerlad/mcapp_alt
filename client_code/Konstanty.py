import anvil.server
# -------------------------------------------------------
# Modul: konstanty
# Obsahuje sdílené konstanty používané napříč aplikací
# -------------------------------------------------------

# Stavy správce stavu
STAV_SPRAVCE = {
    'OK': 'ok',
    'CHYBA': 'error',
    'NEINICIALIZOVANO': 'uninitialized'
}

# Stavy analýzy
STAV_ANALYZY = {
    'NOVY': 'new',
    'UPRAVA': 'edit',
    'ULOZENY': 'saved'
}

# Metody analýzy
METODA_ANALYZY = {
    'SAW': 'SAW',
    'AHP': 'AHP'
}

# Typy kritérií
TYP_KRITERIA = {
    'MAXIMALIZACNI': 'max',
    'MINIMALIZACNI': 'min'
}

# Validační konstanty
VALIDACE = {
    'MAX_DELKA_NAZEV': 100,
    'MIN_POCET_KRITERII': 1,
    'MIN_POCET_VARIANT': 1,
    'TOLERANCE_SOUCTU_VAH': 0.001  # Tolerance pro součet vah (měl by být 1.0)
}

# Chybové zprávy
ZPRAVY_CHYB = {
    # Obecné chyby
    'NEZNAMY_UZIVATEL': 'Pro vytvoření analýzy musíte být přihlášen.',
    'ANALYZA_NEEXISTUJE': 'Analýza s ID {} neexistuje.',
    'NEPLATNE_ID': 'ID analýzy není nastaveno.',
    
    # Validační chyby
    'NAZEV_PRAZDNY': 'Název analýzy nesmí být prázdný.',
    'NAZEV_DLOUHY': f'Název analýzy je příliš dlouhý (max {VALIDACE["MAX_DELKA_NAZEV"]} znaků).',
    'MIN_KRITERIA': f'Je vyžadováno alespoň {VALIDACE["MIN_POCET_KRITERII"]} kritérium.',
    'MIN_VARIANTY': f'Je vyžadována alespoň {VALIDACE["MIN_POCET_VARIANT"]} varianta.',
    'SUMA_VAH': 'Součet vah musí být 1.0 (aktuálně: {}).',
    'NEPLATNA_VAHA': 'Váha musí být číslo mezi 0 a 1.',
    'NEPLATNA_HODNOTA': 'Neplatná hodnota pro variantu {} a kritérium {}.',
    
    # Potvrzovací zprávy
    'POTVRZENI_SMAZANI': 'Opravdu chcete odstranit tuto analýzu?',
    'POTVRZENI_ZRUSENI_NOVE': 'Opustíte rozpracovanou analýzu a data budou smazána. Pokračovat?',
    'POTVRZENI_ZRUSENI_UPRAVY': 'Opustíte upravovanou analýzu. Změny nebudou uloženy. Pokračovat?',
    
    # Úspěch
    'ANALYZA_ULOZENA': 'Analýza byla úspěšně uložena.',

    # Administrace
    'CHYBA_NACTENI_UZIVATELU': 'Chyba při načítání uživatelů: {}',
}

# Popisy hodnot pro uživatele
NAPOVEDA = {
    'VAHA_KRITERIA': 'Zadejte hodnotu váhy mezi 0 a 1 (např. 0.5)',
    'TYP_KRITERIA': {
        'max': 'Čím vyšší hodnota, tím lepší hodnocení',
        'min': 'Čím nižší hodnota, tím lepší hodnocení'
    }
}