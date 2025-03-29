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
        
        # Data analýzy - nová struktura
        self._data_analyzy = {
            "nazev": "",
            "popis_analyzy": "",
            "kriteria": {},
            "varianty": {}
        }
        
        Utils.zapsat_info("Spravce_stavu inicializován s novou strukturou dat")
    
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

    def je_docasne_id(self):
        """
        Ověří, zda aktuální ID analýzy je dočasné.
        
        Returns:
            bool: True pokud je ID dočasné, jinak False
        """
        return self._aktivni_analyza_id == "temp_id"
    
    def ma_neulozena_data(self):
        """
        Kontroluje, zda jsou v cache data, která ještě nebyla uložena na server.
        
        Returns:
            bool: True pokud existují neukládaná data, jinak False
        """
        # Máme data a máme buď dočasné ID nebo jsme v režimu úprav
        return (bool(self._data_analyzy["kriteria"] or self._data_analyzy["varianty"]) and 
                (self.je_docasne_id() or self._rezim_upravy))
  
    def vycisti_data_analyzy(self):
        """
        Vyčistí všechna data související s analýzou.
        """
        self._aktivni_analyza_id = None
        self._rezim_upravy = False
        self._data_analyzy = {
            "nazev": "",
            "popis_analyzy": "",
            "kriteria": {},
            "varianty": {}
        }
        Utils.zapsat_info("Data analýzy vyčištěna")
    
    # === Metody pro práci s daty analýzy ===
    
    def uloz_zakladni_data_analyzy(self, nazev, popis):
        """
        Uloží základní údaje analýzy.
        
        Args:
            nazev (str): Název analýzy
            popis (str): Popis analýzy
        """
        self._data_analyzy["nazev"] = nazev
        self._data_analyzy["popis_analyzy"] = popis
        Utils.zapsat_info(f"Uložena základní data analýzy: {nazev}")
    
    def pridej_kriterium(self, nazev_kriteria, typ, vaha):
        """
        Přidá nové kritérium do cache.
        
        Args:
            nazev_kriteria (str): Název kritéria
            typ (str): Typ kritéria (max nebo min)
            vaha (float): Váha kritéria
        """
        self._data_analyzy["kriteria"][nazev_kriteria] = {
            "typ": typ,
            "vaha": vaha
        }
        Utils.zapsat_info(f"Přidáno kritérium: {nazev_kriteria}")
    
    def uprav_kriterium(self, stary_nazev, novy_nazev, typ, vaha):
        """
        Upraví existující kritérium v cache.
        
        Args:
            stary_nazev (str): Původní název kritéria
            novy_nazev (str): Nový název kritéria
            typ (str): Typ kritéria (max nebo min)
            vaha (float): Váha kritéria
        """
        # Pokud se název nezměnil, jen aktualizujeme
        if stary_nazev == novy_nazev:
            self._data_analyzy["kriteria"][novy_nazev] = {
                "typ": typ,
                "vaha": vaha
            }
        else:
            # Jinak vytvoříme nové a smažeme staré
            self._data_analyzy["kriteria"][novy_nazev] = {
                "typ": typ,
                "vaha": vaha
            }
            del self._data_analyzy["kriteria"][stary_nazev]
            
            # Pokud je kritérium použito u variant, musíme přejmenovat i tam
            for nazev_var, var_data in self._data_analyzy["varianty"].items():
                if stary_nazev in var_data:
                    hodnota = var_data[stary_nazev]
                    var_data[novy_nazev] = hodnota
                    del var_data[stary_nazev]
        
        Utils.zapsat_info(f"Upraveno kritérium: {novy_nazev}")
    
    def smaz_kriterium(self, nazev_kriteria):
        """
        Odstraní kritérium z cache.
        
        Args:
            nazev_kriteria (str): Název kritéria k odstranění
        """
        if nazev_kriteria in self._data_analyzy["kriteria"]:
            del self._data_analyzy["kriteria"][nazev_kriteria]
            
            # Odstraníme kritérium i ze všech variant
            for nazev_var, var_data in self._data_analyzy["varianty"].items():
                if nazev_kriteria in var_data:
                    del var_data[nazev_kriteria]
                    
            Utils.zapsat_info(f"Smazáno kritérium: {nazev_kriteria}")
    
    def pridej_variantu(self, nazev_varianty, popis_varianty=""):
        """
        Přidá novou variantu do cache.
        
        Args:
            nazev_varianty (str): Název varianty
            popis_varianty (str): Popis varianty
        """
        varianta = {"popis_varianty": popis_varianty}
        self._data_analyzy["varianty"][nazev_varianty] = varianta
        Utils.zapsat_info(f"Přidána varianta: {nazev_varianty}")
    
    def uprav_variantu(self, stary_nazev, novy_nazev, popis_varianty):
        """
        Upraví existující variantu v cache.
        
        Args:
            stary_nazev (str): Původní název varianty
            novy_nazev (str): Nový název varianty
            popis_varianty (str): Popis varianty
        """
        # Získáme původní data varianty
        if stary_nazev in self._data_analyzy["varianty"]:
            var_data = self._data_analyzy["varianty"][stary_nazev].copy()
            
            # Aktualizujeme popis
            var_data["popis_varianty"] = popis_varianty
            
            # Pokud se název změnil, vytvoříme novou a smažeme starou
            if stary_nazev != novy_nazev:
                self._data_analyzy["varianty"][novy_nazev] = var_data
                del self._data_analyzy["varianty"][stary_nazev]
            else:
                # Jinak jen aktualizujeme
                self._data_analyzy["varianty"][novy_nazev] = var_data
                
            Utils.zapsat_info(f"Upravena varianta: {novy_nazev}")
    
    def smaz_variantu(self, nazev_varianty):
        """
        Odstraní variantu z cache.
        
        Args:
            nazev_varianty (str): Název varianty k odstranění
        """
        if nazev_varianty in self._data_analyzy["varianty"]:
            del self._data_analyzy["varianty"][nazev_varianty]
            Utils.zapsat_info(f"Smazána varianta: {nazev_varianty}")
    
    def uloz_hodnotu_varianty(self, nazev_varianty, nazev_kriteria, hodnota):
        """
        Uloží hodnotu kritéria pro danou variantu.
        
        Args:
            nazev_varianty (str): Název varianty
            nazev_kriteria (str): Název kritéria
            hodnota (float): Hodnota kritéria pro danou variantu
        """
        if nazev_varianty in self._data_analyzy["varianty"]:
            self._data_analyzy["varianty"][nazev_varianty][nazev_kriteria] = hodnota
            Utils.zapsat_info(f"Uložena hodnota pro variantu {nazev_varianty}, kritérium {nazev_kriteria}: {hodnota}")
    
    def ziskej_nazev(self):
        """
        Vrátí název analýzy.
        
        Returns:
            str: Název analýzy
        """
        return self._data_analyzy.get("nazev", "")
    
    def ziskej_popis(self):
        """
        Vrátí popis analýzy.
        
        Returns:
            str: Popis analýzy
        """
        return self._data_analyzy.get("popis_analyzy", "")
    
    def ziskej_kriteria(self):
        """
        Vrátí kritéria analýzy.
        
        Returns:
            dict: Slovník kritérií
        """
        return self._data_analyzy.get("kriteria", {})
    
    def ziskej_varianty(self):
        """
        Vrátí varianty analýzy.
        
        Returns:
            dict: Slovník variant
        """
        return self._data_analyzy.get("varianty", {})
    
    def uloz_analyzu_na_server(self):
        """
        Uloží kompletní analýzu na server.
        
        Returns:
            bool: True pokud uložení proběhlo úspěšně, jinak False
        """
        try:
            # Kontrola, zda jde o novou analýzu nebo aktualizaci
            je_nova = not self._aktivni_analyza_id or self._aktivni_analyza_id == "temp_id"
            
            if je_nova:
                # Vytvoření nové analýzy
                analyza_id = anvil.server.call('vytvor_analyzu', 
                                               self._data_analyzy.get("nazev", ""), 
                                               self._data_analyzy.get("popis_analyzy", ""))
                
                if not analyza_id:
                    Utils.zapsat_chybu("Nepodařilo se vytvořit novou analýzu")
                    return False
                    
                # Uložení ID do správce stavu
                self._aktivni_analyza_id = analyza_id
                Utils.zapsat_info(f"Vytvořena nová analýza s ID: {analyza_id}")
            
            # Příprava dat pro uložení/aktualizaci
            data = {
                "popis_analyzy": self._data_analyzy.get("popis_analyzy", ""),
                "kriteria": self._data_analyzy.get("kriteria", {}),
                "varianty": self._data_analyzy.get("varianty", {})
            }
            
            # Uložení/aktualizace dat analýzy
            anvil.server.call('uprav_analyzu', 
                              self._aktivni_analyza_id,
                              self._data_analyzy.get("nazev", ""),
                              data)
            
            Utils.zapsat_info(f"Analýza úspěšně uložena: {self._aktivni_analyza_id}")
            return True
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při ukládání analýzy: {str(e)}")
            return False