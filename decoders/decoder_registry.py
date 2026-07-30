# decoders/decoder_registry.py
from . import rc6
from . import rc5
from . import nrc17
from . import rcmm
from . import kaseikyo
from . import bo          # NEW
from . import xmp         # NEW
from . import nec
from . import onkyo
from . import apple
from . import sanyo
from . import lg
from . import samsung
from . import rca
from . import sony
from . import jvc
from . import panasonic
from . import zenith
from . import sharp
from . import denon

def try_all_decoders(mark_space_array):
    """Passes the array to every loaded decoder until one returns Success."""
    
    # 1. Try RC6
    rc6_result = rc6.decode(mark_space_array)
    if rc6_result.get("status") == "Success": return rc6_result

    # 2. Try RC5
    rc5_result = rc5.decode(mark_space_array)
    if rc5_result.get("status") == "Success": return rc5_result

    # 3. Try NRC17
    nrc17_result = nrc17.decode(mark_space_array)
    if nrc17_result.get("status") == "Success": return nrc17_result
        
    # 4. Try RC-MM
    rcmm_result = rcmm.decode(mark_space_array)
    if rcmm_result.get("status") == "Success": return rcmm_result
        
    # 5. Try Kaseikyo (Generic)
    kaseikyo_result = kaseikyo.decode(mark_space_array)
    if kaseikyo_result.get("status") == "Success": return kaseikyo_result

    # 6.Try Bang & Olufsen
    bo_result = bo.decode(mark_space_array)
    if bo_result.get("status") == "Success": return bo_result

    # 7. Try XMP
    xmp_result = xmp.decode(mark_space_array)
    if xmp_result.get("status") == "Success": return xmp_result

    # 8. Try NEC
    nec_result = nec.decode(mark_space_array)
    if nec_result.get("status") in ["Success", "Repeat"]: return nec_result
        
    # 9. Try Onkyo (Fallback for NEC-style 32-bit signals)
    onkyo_result = onkyo.decode(mark_space_array)
    if onkyo_result.get("status") in ["Success", "Repeat"]: return onkyo_result
        
    # 10. Try Apple (Fallback for NEC-style 32-bit signals with Apple Vendor IDs)
    apple_result = apple.decode(mark_space_array)
    if apple_result.get("status") in ["Success", "Repeat"]: return apple_result
        
    # 11. Try Sanyo (Fallback for NEC-style 42-bit signals)
    sanyo_result = sanyo.decode(mark_space_array)
    if sanyo_result.get("status") in ["Success", "Repeat"]: return sanyo_result
        
    # 12. Try LG
    lg_result = lg.decode(mark_space_array)
    if lg_result.get("status") in ["Success", "Repeat"]: return lg_result
        
    # 13. Try Samsung
    samsung_result = samsung.decode(mark_space_array)
    if samsung_result.get("status") == "Success": return samsung_result
        
    # 14. Try Panasonic
    panasonic_result = panasonic.decode(mark_space_array)
    if panasonic_result.get("status") == "Success": return panasonic_result
        
    # 15. Try RCA
    rca_result = rca.decode(mark_space_array)
    if rca_result.get("status") == "Success": return rca_result
        
    # 16. Try Sony
    sony_result = sony.decode(mark_space_array)
    if sony_result.get("status") == "Success": return sony_result

    # 17. Try JVC
    jvc_result = jvc.decode(mark_space_array)
    if jvc_result.get("status") == "Success": return jvc_result
        
    # 18. Try Zenith (Checked last as it has no header)
    zenith_result = zenith.decode(mark_space_array)
    if zenith_result.get("status") == "Success": return zenith_result

    # 19. Try Sharp (Checked last as it has no header)
    sharp_result = sharp.decode(mark_space_array)
    if sharp_result.get("status") == "Success": return sharp_result

    # 20. Try Denon (Checked last as it has no header)
    denon_result = denon.decode(mark_space_array)
    if denon_result.get("status") == "Success": return denon_result

    # If all fail, return an unknown state
    return {"status": "Error", "message": "Unknown Protocol"}