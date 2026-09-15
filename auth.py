#!/usr/bin/env python3
"""
auth.py — LMS Polinema MCP Setup Script

Automated Browser Flow:
1. Buka SIAKAD Polinema login page di Chromium
2. Isi NIM & Password -> Klik tombol Login
3. Di Beranda SIAKAD, klik menu 'Akademik' -> klik submenu 'LMS'
4. Tunggu tombol 'Connect to LMS Polinema' muncul, lalu klik
5. Browser otomatis dialihkan ke slc.polinema.ac.id / SPADA -> LMS
6. Tangkap POLIMASPADA & MoodleSession cookies
7. Simpan ke ~/.lms_polinema/

Usage: python auth.py
"""

import getpass
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from lms_polinema_mcp.auth.session import SessionManager
from lms_polinema_mcp.config import (
    INSTITUTION,
    MOODLE_BASE_URL,
    MOODLE_SESSION_FILE,
    SESSION_DIR,
    SIAKAD_BASE_URL,
    SPADA_BASE_URL,
    SPADA_SESSION_FILE,
)

SEP = "─" * 56


def main():
    print(f"\n{SEP}")
    print(f"  LMS {INSTITUTION} MCP — Interactive Authentication")
    print(f"  Flow: Login SIAKAD -> Menu Akademik -> LMS -> Connect to LMS")
    print(f"{SEP}\n")

    manager = SessionManager()
    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    print("Masukkan akun SIAKAD Polinema kamu:")
    username = input("NIM     : ").strip()
    if not username:
        print("❌ NIM tidak boleh kosong.")
        sys.exit(1)

    password = getpass.getpass("Password: ")
    if not password:
        print("❌ Password tidak boleh kosong.")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    except ImportError:
        print("❌ Playwright belum terinstall.")
        sys.exit(1)

    print("\n🌐 Membuka browser Chromium...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=400)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        # Step 1: Buka Login SIAKAD
        print("⏳ [1/4] Membuka halaman login SIAKAD...")
        page.goto(f"{SIAKAD_BASE_URL}/login", wait_until="networkidle")

        page.fill("#username", username)
        page.fill("#password", password)
        page.click("button[type='submit']")

        print("⏳ [2/4] Melakukan login di SIAKAD...")
        try:
            page.wait_for_url(lambda u: "/login" not in u, timeout=25_000)
            print("✅ Berhasil masuk ke Beranda SIAKAD!")
        except PlaywrightTimeout:
            err_text = ""
            try:
                err_text = page.locator("#alert-login").inner_text()
            except Exception:
                pass
            print(f"❌ Login SIAKAD gagal: {err_text}")
            browser.close()
            sys.exit(1)

        # Beri waktu render beranda
        time.sleep(2)

        # Step 2: Buka menu Akademik -> LMS
        print("⏳ [3/4] Mengarahkan ke menu Akademik > LMS...")
        try:
            # Klik menu Akademik jika dropdown belum terbuka
            akademik_menu = page.locator("a:has-text('Akademik'), span:has-text('Akademik')").first
            if akademik_menu.is_visible():
                akademik_menu.click()
                time.sleep(1)

            # Klik submenu LMS
            lms_submenu = page.locator("a[href*='slc'], a:has-text('LMS')").first
            if lms_submenu.is_visible():
                lms_submenu.click()
            else:
                # Direct navigation fallback
                page.goto(f"{SIAKAD_BASE_URL}/mahasiswa/slc/index/gm/akademik", wait_until="networkidle")
        except Exception as e:
            print(f"   Navigasi via menu error ({e}), mencoba akses langsung...")
            page.goto(f"{SIAKAD_BASE_URL}/mahasiswa/slc/index/gm/akademik", wait_until="networkidle")

        # Step 3: Klik tombol "Connect to LMS Polinema"
        print("⏳ [4/4] Mencari tombol 'Connect to LMS Polinema'...")
        try:
            connect_btn = page.locator("text='Connect to LMS Polinema', a:has-text('Connect to LMS Polinema'), button:has-text('Connect to LMS Polinema')").first
            connect_btn.wait_for(state="visible", timeout=15_000)
            print("👉 Mengklik 'Connect to LMS Polinema'...")
            
            # Tombol ini biasanya membuka tab baru (target="_blank") atau redirect langsung
            with context.expect_page(timeout=10_000) as new_page_info:
                connect_btn.click()
            new_page = new_page_info.value
            new_page.wait_for_load_state("networkidle")
            print(f"✅ Halaman baru terbuka: {new_page.url}")
        except PlaywrightTimeout:
            # Jika tidak membuka tab baru melainkan redirect di halaman yang sama
            print("   Tombol redirect di halaman yang sama...")
            try:
                page.locator("text='Connect to LMS Polinema'").first.click()
                time.sleep(5)
            except Exception as e:
                print(f"⚠️  Gagal mengklik tombol otomatis: {e}")
                print("   Silakan klik tombol 'Connect to LMS Polinema' secara manual di browser yang terbuka!")
                time.sleep(15)
        except Exception as e:
            print(f"⚠️  {e}. Silakan klik tombol 'Connect to LMS Polinema' manual di browser!")
            time.sleep(15)

        print("\n⏳ Mengambil sesi dari browser...")
        time.sleep(4)

        # Kumpulkan semua cookie dari seluruh tab/pages
        all_cookies = {}
        for c in context.cookies():
            all_cookies[c["name"]] = c["value"]

        for pg in context.pages:
            try:
                for c in pg.context.cookies():
                    all_cookies[c["name"]] = c["value"]
            except Exception:
                pass

        polimaspada = all_cookies.get("POLIMASPADA", "")
        moodle_session = all_cookies.get("MoodleSession", "")

        # Jika sudah di SPADA tapi MoodleSession belum aktif, buka course link di SPADA
        if polimaspada and not moodle_session:
            print("⏳ Menghubungkan sesi ke lmsslc.polinema.ac.id...")
            try:
                p_spada = context.new_page()
                p_spada.goto(f"{SPADA_BASE_URL}/?mod=matakuliah", wait_until="networkidle")
                time.sleep(2)
                course_link = p_spada.locator("a[href*='lmsslc.polinema.ac.id']").first
                if course_link.count() > 0:
                    with context.expect_page() as lms_page_info:
                        course_link.click()
                    lms_page = lms_page_info.value
                    lms_page.wait_for_load_state("networkidle")
                    time.sleep(3)
            except Exception as e:
                print(f"   (Info: {e})")

        # Refresh cookies
        for c in context.cookies():
            all_cookies[c["name"]] = c["value"]
        polimaspada = all_cookies.get("POLIMASPADA", polimaspada)
        moodle_session = all_cookies.get("MoodleSession", moodle_session)

        browser.close()

        print("\n" + SEP)
        if polimaspada:
            SPADA_SESSION_FILE.write_text(json.dumps({
                "POLIMASPADA": polimaspada,
                "saved_at": time.time()
            }, indent=2))
            print(f"✅ Sesi SPADA tersimpan : POLIMASPADA={polimaspada[:8]}...")

        if moodle_session:
            manager.save(moodle_session)
            print(f"✅ Sesi Moodle tersimpan: MoodleSession={moodle_session[:8]}...")

        if polimaspada or moodle_session:
            print("\n🎉 Autentikasi BERHASIL!")
            print(f"Sesi disimpan di {SESSION_DIR}/")
        else:
            print("\n❌ Sesi belum tertangkap. Pastikan tombol Connect to LMS ditekan.")
        print(SEP + "\n")


if __name__ == "__main__":
    main()
