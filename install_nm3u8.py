#!/usr/bin/env python3
"""
YUNA-System N_m3u8DL-RE Installation Utility
Semplice script per installare e configurare N_m3u8DL-RE
"""

import sys
import argparse

# Add src to path
sys.path.insert(0, "src")

from yuna.utils.nm3u8_installer import install_nm3u8, Nm3u8Installer


def main():
    parser = argparse.ArgumentParser(
        description="Install N_m3u8DL-RE per YUNA-System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python install_nm3u8.py               # Installazione automatica
  python install_nm3u8.py --check        # Verifica installazione
  python install_nm3u8.py --force        # Reinstallazione forzata
  python install_nm3u8.py --dir /usr/bin # Installa in directory specifica
        """
    )
    
    parser.add_argument(
        "--force", 
        action="store_true",
        help="Forza la reinstallazione anche se già installato"
    )
    
    parser.add_argument(
        "--dir", 
        help="Directory di installazione (auto-rilevata se non specificata)"
    )
    
    parser.add_argument(
        "--check", 
        action="store_true",
        help="Verifica se N_m3u8DL-RE è già installato e funzionante"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Output dettagliato durante l'installazione"
    )
    
    args = parser.parse_args()
    
    # Configurazione logging
    import logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    if args.check:
        print("🔍 Verifica installazione N_m3u8DL-RE...")
        installer = Nm3u8Installer()
        if installer.check_installed():
            print("✅ N_m3u8DL-RE è installato e funzionante")
            
            # Show version
            import subprocess
            try:
                result = subprocess.run(
                    ["N_m3u8DL-RE", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    print(f"📦 Versione: {result.stdout.strip()}")
            except:
                pass
                
            return 0
        else:
            print("❌ N_m3u8DL-RE non è installato o non funzionante")
            print("💡 Esegui 'python install_nm3u8.py' per installarlo")
            return 1
    
    # Installazione
    print("🚀 Inizio installazione N_m3u8DL-RE per YUNA-System...")
    print("Questo installer scaricherà l'ultima versione da GitHub.")
    print()
    
    if install_nm3u8(force=args.force, install_dir=args.dir):
        print()
        print("✅ Installazione completata con successo!")
        print()
        print("🎯 YUNA-System ora utilizzerà N_m3u8DL-RE per download più veloci:")
        print("   • Download paralleli fino a 16 thread")
        print("   • Miglior gestione degli errori")
        print("   • Supporto avanzato per HLS/DASH")
        print("   • Auto-selezione della qualità migliore")
        print()
        print("⚙️  Puoi configurare le opzioni di download nel file .env:")
        print("   PREFER_NM3U8=true        # Usa N_m3u8DL-RE (default)")
        print("   NM3U8_THREAD_COUNT=16    # Thread paralleli")
        print("   NM3U8_MAX_SPEED=15M      # Limite velocità")
        print()
        print("🔄 Riavvia YUNA-System per applicare le modifiche.")
        return 0
    else:
        print()
        print("❌ Installazione fallita!")
        print()
        print("🔧 Possibili soluzioni:")
        print("   • Controlla la connessione internet")
        print("   • Prova con 'sudo python install_nm3u8.py' (permessi)")
        print("   • Specifica una directory con '--dir /percorso/permessivo'")
        print()
        print("📝 YUNA-System continuerà a usare ffmpeg come fallback.")
        return 1


if __name__ == "__main__":
    sys.exit(main())