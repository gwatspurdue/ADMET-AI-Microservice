from admet_ai import ADMETModel
from pydantic import BaseModel, create_model
from typing import Optional, Dict, Any
import argparse
import torch
import numpy
import sys

# Due to the size of the data, we switch to a dynamic generation of
# parameters and methods versus a static one

# ------------------------------------------------------------------------
# 1. DEFINE RAW PROPERTY TABLE
# ------------------------------------------------------------------------

# Format: (id, name, task_type)
# id  -> dictionary key from your model output
# name -> friendly human-readable name (not used for field names)
# task_type -> "regression" or "classification" (determines field type)

ALL_PROPS = [
    ("molecular_weight", "Molecular Weight", "regression"),
    ("logP", "LogP", "regression"),
    ("hydrogen_bond_acceptors", "Hydrogen Bond Acceptors", "regression"),
    ("hydrogen_bond_donors", "Hydrogen Bond Donors", "regression"),
    ("Lipinski", "Lipinski Rule of 5", "regression"),
    ("QED", "Quantitative Estimate of Druglikeness", "regression"),
    ("stereo_centers", "Stereo Centers", "regression"),
    ("tpsa", "Topological Polar Surface Area", "regression"),

    # Absorption
    ("HIA_Hou", "Human Intestinal Absorption", "classification"),
    ("Bioavailability_Ma", "Oral Bioavailability", "classification"),
    ("Solubility_AqSolDB", "Aqueous Solubility", "regression"),
    ("Lipophilicity_AstraZeneca", "Lipophilicity", "regression"),
    ("HydrationFreeEnergy_FreeSolv", "Hydration Free Energy", "regression"),
    ("Caco2_Wang", "Caco2 Permeability", "regression"),
    ("PAMPA_NCATS", "PAMPA Permeability", "classification"),
    ("Pgp_Broccatelli", "P-glycoprotein Inhibition", "classification"),

    # Distribution
    ("BBB_Martins", "Blood-Brain Barrier Penetration", "classification"),
    ("PPBR_AZ", "Plasma Protein Binding Rate", "regression"),
    ("VDss_Lombardo", "Volume of Distribution Steady State", "regression"),

    # Excretion
    ("Half_Life_Obach", "Half-Life", "regression"),
    ("Clearance_Hepatocyte_AZ", "Drug Clearance Hepatocyte", "regression"),
    ("Clearance_Microsome_AZ", "Drug Clearance Microsome", "regression"),

    # Metabolism
    ("CYP1A2_Veith", "CYP1A2 Inhibition", "classification"),
    ("CYP2C19_Veith", "CYP2C19 Inhibition", "classification"),
    ("CYP2C9_Veith", "CYP2C9 Inhibition", "classification"),
    ("CYP2D6_Veith", "CYP2D6 Inhibition", "classification"),
    ("CYP3A4_Veith", "CYP3A4 Inhibition", "classification"),
    ("CYP2C9_Substrate_CarbonMangels", "CYP2C9 Substrate", "classification"),
    ("CYP2D6_Substrate_CarbonMangels", "CYP2D6 Substrate", "classification"),
    ("CYP3A4_Substrate_CarbonMangels", "CYP3A4 Substrate", "classification"),

    # Toxicity
    ("hERG", "hERG Blocking", "classification"),
    ("ClinTox", "Clinical Toxicity", "classification"),
    ("AMES", "AMES Mutagenicity", "classification"),
    ("DILI", "Drug Induced Liver Injury", "classification"),
    ("Carcinogens_Lagunin", "Carcinogenicity", "classification"),
    ("LD50_Zhu", "Acute Toxicity LD50", "regression"),
    ("Skin_Reaction", "Skin Reaction", "classification"),
    ("NR-AR", "Androgen Receptor", "classification"),
    ("NR-AR-LBD", "Androgen Receptor LBD", "classification"),
    ("NR-AhR", "Aryl Hydrocarbon Receptor", "classification"),
    ("NR-Aromatase", "Aromatase", "classification"),
    ("NR-ER", "Estrogen Receptor", "classification"),
    ("NR-ER-LBD", "Estrogen Receptor LBD", "classification"),
    ("NR-PPAR-gamma", "PPAR-gamma", "classification"),
    ("SR-ARE", "ARE", "classification"),
    ("SR-ATAD5", "ATAD5", "classification"),
    ("SR-HSE", "HSE", "classification"),
    ("SR-MMP", "Mitochondrial Membrane Potential", "classification"),
    ("SR-p53", "p53", "classification"),
]

# ------------------------------------------------------------------------
# 2. CREATE PROPERTY NAME MAPPING
# ------------------------------------------------------------------------

# Create a mapping from friendly names (lowercase) to full property IDs
PROPERTY_NAME_MAP = {}
for pid, friendly_name, _ in ALL_PROPS:
    # Map full ID
    PROPERTY_NAME_MAP[pid] = pid
    # Map lowercase version of ID
    PROPERTY_NAME_MAP[pid.lower()] = pid
    # Map friendly name lowercase
    PROPERTY_NAME_MAP[friendly_name.lower().replace(" ", "_")] = pid

# ------------------------------------------------------------------------
# 3. CREATE Pydantic MODEL PROGRAMMATICALLY
# ------------------------------------------------------------------------

def make_pydantic_model():
    """Dynamically create the Admet_Return model with all fields."""
    fields = {}
    for pid, _, task in ALL_PROPS:
        fields[pid] = (Optional[float], None)

    return create_model(
        "Admet_Return",
        **fields,
        __base__=BaseModel
    )

Admet_Return = make_pydantic_model()

# ------------------------------------------------------------------------
# 4. CREATE Admet() CLASS WITH GETTERS + as_obj()
# ------------------------------------------------------------------------

class Admet:
    def __init__(self):
        """
        model must have .predict(smiles) -> dict keyed by property ID.
        """
        torch.serialization.add_safe_globals([
            argparse.Namespace,
            numpy.ndarray, numpy.core.multiarray._reconstruct, numpy.dtype,
            numpy.dtype('float64').__class__])
        self.model = ADMETModel()
        self.preds: Dict[str, Any] = {}

    def run(self, smi: str):
        self.preds = self.model.predict(smi)

    # Generate getters dynamically
    def __getattr__(self, name):
        """
        Enables functions like: admet.get_logP(), admet.get_hERG(), etc.
        Supports both full property IDs and friendly names.
        """
        if name.startswith("get_"):
            prop = name[4:]  # remove "get_"
            # Map the property name to the full ID
            full_prop_id = PROPERTY_NAME_MAP.get(prop)
            if full_prop_id and full_prop_id in self.preds:
                return lambda p=full_prop_id: self.preds[p]
        raise AttributeError(name)

    def as_obj(self) -> Admet_Return:
        """
        Returns a fully formed Pydantic model with all fields populated.
        Missing predictions stay None.
        """
        return Admet_Return(**self.preds)
