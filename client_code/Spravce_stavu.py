# -------------------------------------------------------
# Modul: Spravce_stavu 
# -------------------------------------------------------

import anvil.server
import anvil.users
from . import Utils

class Spravce_stavu:
    """
    Třída pro centralizovanou správu stavu aplikace.
    Implementovaná jako singleton pro zajištění konzistence stavu napříč komponentami.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Spravce_stavu, cls).__new__(cls)
            cls._instance.inicializuj()
        return cls._instance
    
    def inicializuj(self):
        """
        Inicializuje stav aplikace na výchozí hodnoty.
        Tato metoda je volána pouze jednou při vytvoření instance.
        """
        # Stav uživatele
        self._prihlaseny_uzivatel = None
        self._je_admin = False
        
        # Stav analýzy
        self._aktivni_analyza_id = None
        self._rezim_upravy = False
        
        # Cache dat
        self._data_analyzy = {}
        self._data_kriterii = []
        self._data_variant = []
        self._data_hodnot = {'matice_hodnoty': {}}
        
        Utils.zapsat_info("Spravce_stavu inicializován")
    
    # === Metody pro práci s uživatelem ===
    
    def nacti_uzivatele(self):
        """
        Načte a uloží informace o přihlášeném uživateli.
        
        Returns:
            dict: Informace o uživateli nebo None pokud není přihlášen
        """
        try:
            self._prihlaseny_uzivatel = anvil.users.get_user()
            
            if self._prihlaseny_uzivatel:
                try:
                    self._je_admin = self._prihlaseny_uzivatel['role'] == 'admin'
                except KeyError:
                    self._je_admin = False
                
                Utils.zapsat_info(f"Uživatel načten: {self._prihlaseny_uzivatel['email']}")
            else:
                self._je_admin = False
                Utils.zapsat_info("Žádný uživatel není přihlášen")
                
            return self._prihlaseny_uzivatel
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při načítání uživatele: {str(e)}")
            self._prihlaseny_uzivatel = None
            self._je_admin = False
            return None
    
    def je_prihlasen(self):
        """
        Zjistí, zda je uživatel přihlášen.
        
        Returns:
            bool: True pokud je uživatel přihlášen, jinak False
        """
        if self._prihlaseny_uzivatel is None:
            self.nacti_uzivatele()
        return self._prihlaseny_uzivatel is not None
    
    def je_admin(self):
        """
        Zjistí, zda má přihlášený uživatel administrátorská práva.
        
        Returns:
            bool: True pokud je uživatel admin, jinak False
        """
        if not self.je_prihlasen():
            return False
        return self._je_admin
    
    def odhlasit(self):
        """
        Odhlásí uživatele a vyčistí jeho data.
        """
        self._prihlaseny_uzivatel = None
        self._je_admin = False
        self.vycisti_data_analyzy()
    
    # === Metody pro práci s analýzou ===
    
    def nastav_aktivni_analyzu(self, analyza_id, rezim_upravy=False):
        """
        Nastaví ID aktivní analýzy a její režim.
        
        Args:
            analyza_id (str): ID analýzy
            rezim_upravy (bool): Zda je analýza v režimu úprav
        """
        self._aktivni_analyza_id = analyza_id
        self._rezim_upravy = rezim_upravy
        Utils.zapsat_info(f"Aktivní analýza nastavena: {analyza_id}, režim úprav: {rezim_upravy}")
    
    def ziskej_aktivni_analyzu(self):
        """
        Vrátí ID aktivní analýzy.
        
        Returns:
            str: ID aktivní analýzy nebo None
        """
        return self._aktivni_analyza_id
    
    def je_rezim_upravy(self):
        """
        Zjistí, zda je analýza v režimu úprav.
        
        Returns:
            bool: True pokud je analýza v režimu úprav, jinak False
        """
        return self._rezim_upravy
    
    def vycisti_data_analyzy(self):
        """
        Vyčistí všechna data související s analýzou.
        """
        self._aktivni_analyza_id = None
        self._rezim_upravy = False
        self._data_analyzy = {}
        self._data_kriterii = []
        self._data_variant = []
        self._data_hodnot = {'matice_hodnoty': {}}
    
    # === Metody pro práci s daty analýzy ===
    
    def uloz_data_analyzy(self, data):
        """
        Uloží základní data analýzy.
        
        Args:
            data (dict): Data analýzy
        """
        self._data_analyzy = data
    
    def uloz_kriteria(self, kriteria):
        """
        Uloží kritéria analýzy.
        
        Args:
            kriteria (list): Seznam kritérií
        """
        self._data_kriterii = kriteria
    
    def uloz_varianty(self, varianty):
        """
        Uloží varianty analýzy.
        
        Args:
            varianty (list): Seznam variant
        """
        self._data_variant = varianty
    
    def uloz_hodnoty(self, hodnoty):
        """
        Uloží hodnoty matice analýzy.
        
        Args:
            hodnoty (dict): Slovník s hodnotami matice
        """
        self._data_hodnot = hodnoty
    
    def ziskej_data_analyzy(self):
        """
        Vrátí základní data analýzy.
        
        Returns:
            dict: Data analýzy
        """
        return self._data_analyzy
    
    def ziskej_kriteria(self):
        """
        Vrátí kritéria analýzy.
        
        Returns:
            list: Seznam kritérií
        """
        return self._data_kriterii
    
    def ziskej_varianty(self):
        """
        Vrátí varianty analýzy.
        
        Returns:
            list: Seznam variant
        """
        return self._data_variant
    
    def ziskej_hodnoty(self):
        """
        Vrátí hodnoty matice analýzy.
        
        Returns:
            dict: Slovník s hodnotami matice
        """
        return self._data_hodnot
    
    # === Metody pro načítání dat ze serveru ===
    
    def nacti_kompletni_analyzu_ze_serveru(self, analyza_id=None):
        """
        Načte kompletní data analýzy ze serveru a uloží je lokálně.
        
        Args:
            analyza_id (str, optional): ID analýzy. Pokud není zadáno, použije se aktivní analýza.
            
        Returns:
            bool: True pokud načtení proběhlo úspěšně, jinak False
        """
        if not analyza_id and not self._aktivni_analyza_id:
            Utils.zapsat_chybu("Není zvolena žádná analýza pro načtení")
            return False
            
        id_pro_nacteni = analyza_id or self._aktivni_analyza_id
        
        try:
            data = anvil.server.call('nacti_kompletni_analyzu', id_pro_nacteni)
            
            if data:
                self._data_analyzy = data['analyza']
                self._data_kriterii = data['kriteria']
                self._data_variant = data['varianty']
                self._data_hodnot = data['hodnoty']
                self._aktivni_analyza_id = id_pro_nacteni
                
                Utils.zapsat_info(f"Analýza úspěšně načtena: {id_pro_nacteni}")
                return True
            else:
                Utils.zapsat_chybu(f"Server nevrátil žádná data pro analýzu: {id_pro_nacteni}")
                return False
                
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při načítání analýzy: {str(e)}")
            return False