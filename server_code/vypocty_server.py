# import anvil.server
# from skcriteria.core.data import mkdm
# from skcriteria.preprocessing.scalers import MinMaxScaler
# from skcriteria.preprocessing.invert_objectives import InvertMinimize
# from skcriteria.pipeline import mkpipe
# from skcriteria.agg.simple import WeightedSumModel
# import numpy as np

# @anvil.server.callable
# def vypocet_normalizace(analyza_data):
#     """
#     Performs analysis normalization using scikit-criteria (WeightedSumModel with set normalization).
#     In this example, we focus only on the normalized matrix, ignoring overall scores and rankings.
    
#     Args:
#         analyza_data (dict): Analysis data with structure:
#             {
#               'varianty': [{'nazev_varianty':..., ...}, ...],  # alternatives
#               'kriteria': [{'nazev_kriteria':..., 'typ':..., 'vaha':...}, ...],  # criteria
#               'hodnoty': {
#                 'matice_hodnoty': { 'DodavatelA_Cena': 123, ... }  # matrix values
#               }
#             }
            
#     Returns:
#         dict: Dictionary with normalized matrix and additional info:
#         {
#             'nazvy_variant': [...],  # alternative names
#             'nazvy_kriterii': [...],  # criteria names
#             'normalizovana_matice': [[...], [...], ...],  # 2D normalized matrix
#             'zprava': "OK"  # status message
#         }
#     """
#     # 1) Loading and preparing inputs
#     varianty = analyza_data['varianty']
#     kriteria = analyza_data['kriteria']
#     matice_hodnot = analyza_data['hodnoty']['matice_hodnoty']
    
#     # Names for scikit-criteria
#     anames = [v['nazev_varianty'] for v in varianty]
#     cnames = [k['nazev_kriteria'] for k in kriteria]
    
#     # Define objectives (minimize/maximize)
#     objectives = []
#     for k in kriteria:
#         if k['typ'].lower() in ("max", "benefit"):
#             objectives.append(1)  # 1 for maximize
#         else:
#             objectives.append(-1)  # -1 for minimize
            
#     # Weights for criteria
#     weights = np.array([float(k['vaha']) for k in kriteria])
    
#     # 2) Building the matrix
#     mtx = []
#     for var in varianty:
#         row = []
#         for krit in kriteria:
#             kl = f"{var['nazev_varianty']}_{krit['nazev_kriteria']}"
#             hod = matice_hodnot.get(kl, 0)
#             row.append(float(hod))
#         mtx.append(row)
    
#     # 3) Creating DecisionMatrix
#     dm = mkdm(
#         mtx,
#         objectives=objectives,
#         weights=weights,
#         alternatives=anames,
#         criteria=cnames
#     )
    
#     # 4) Create the scaler and apply it directly
#     scaler = MinMaxScaler(target='matrix')
#     normalized_dm = scaler.transform(dm)
    
#     # Get the normalized matrix - convert from DataFrame to list
#     normalizovana = normalized_dm.matrix.values.tolist()
    
#     # 5) Returning results
#     return {
#         'nazvy_variant': anames,
#         'nazvy_kriterii': cnames,
#         'normalizovana_matice': normalizovana,
#         'zprava': "OK - Normalizace hotová"
#     }

