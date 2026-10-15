# This file is part of YuleeSelf-UwU.
# Copyright (c) 2025-Present Routo
#
# YuleeSelf-UwU is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with YuleeSelf-UwU. If not, see <https://www.gnu.org/licenses/>.


"""
Author: zOnisdev
YuleeSelf-UwU - https://github.com/itsyulee/yulee-self
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import time
import argparse
from importlib.metadata import version

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import core.state as state
from yulee_engines.setup_engine import YuleeSetupEngine, console, Confirm, Prompt, Table, Panel
from utils import proxy_manager

engine = YuleeSetupEngine()

from yuleeself_ascii.yulee_ascii import show_banner

def clean_screen():
    os.system("cls" if os.name == "nt" else "clear")

def show_accounts(accounts):
    if not accounts:
        console.print("[dim]no accounts yet.[/dim]")
        return
    proxies = {p["id"]: p for p in engine.load_proxies()}
    table = Table(border_style="red")
    table.add_column("no.", justify="center")
    table.add_column("name")
    table.add_column("token")
    table.add_column("proxy")
    table.add_column("status", justify="center")
    for idx, acc in enumerate(accounts):
        tk = acc.get("token", "")
        preview = f"{tk[:6]}...{tk[-4:]}" if len(tk) > 10 else tk
        active = "[green]enabled[/green]" if acc.get("enabled", True) else "[red]disabled[/red]"
        pid = acc.get("proxy_id")
        proxy_label = "direct"
        if pid and pid in proxies:
            p = proxies[pid]
            proxy_label = p.get("label") or f"{p.get('host')}:{p.get('port')}"
        table.add_row(str(idx + 1), acc.get("name", "user"), preview, proxy_label, active)
    console.print(table)

def _pick_proxy():
    proxies = engine.load_proxies()
    choices = [("0", "none (direct)")]
    for i, p in enumerate(proxies, 1):
        label = p.get("label") or f"{p.get('host')}:{p.get('port')}"
        choices.append((str(i), f"{label} [{p.get('type', 'socks5')}]"))
    if len(choices) == 1:
        return None
    console.print("\n[dim]select proxy (optional):[/dim]")
    for key, label in choices:
        console.print(f"  [{key}] {label}")
    pick = Prompt.ask("proxy", default="0")
    if pick == "0":
        return None
    try:
        idx = int(pick) - 1
        if 0 <= idx < len(proxies):
            return proxies[idx].get("id")
    except ValueError:
        pass
    return None

async def account_manager(add_only=False):
    accounts = engine.load_accounts()
    while True:
        show_banner('setup', animate=False)
        console.print("[bold white] account management [/bold white]\n")
        show_accounts(accounts)
        if add_only:
            action = "1"
        else:
            console.print("\n[1] add  [2] remove  [3] toggle  [4] verify  [5] bulk import  [6] back")
            action = Prompt.ask("action", choices=["1", "2", "3", "4", "5", "6"], default="6")
        if action == "1":
            name = Prompt.ask("account name")
            token = Prompt.ask("token").strip()
            if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
                token = token[1:-1]
            channels_raw = Prompt.ask("channel ids (space separated)")
            channel_ids = channels_raw.split()
            proxy_id = _pick_proxy()
            accounts.append({
                "name": name,
                "token": token,
                "channels": channel_ids,
                "enabled": True,
                "proxy_id": proxy_id,
            })
            engine.save_accounts(accounts)
            console.print("[green]account saved.[/green]")
            if add_only:
                return
            time.sleep(1)
        elif action == "2":
            if not accounts:
                continue
            idx = int(Prompt.ask("no. to delete", default="1")) - 1
            if 0 <= idx < len(accounts):
                accounts.pop(idx)
                engine.save_accounts(accounts)
                console.print("[red]removed.[/red]")
            time.sleep(1)
        elif action == "3":
            if not accounts:
                continue
            idx = int(Prompt.ask("no. to toggle", default="1")) - 1
            if 0 <= idx < len(accounts):
                accounts[idx]["enabled"] = not accounts[idx].get("enabled", True)
                engine.save_accounts(accounts)
                console.print("[yellow]toggled.[/yellow]")
            time.sleep(1)
        elif action == "4":
            if not accounts:
                continue
            console.print("\n[bold cyan]1.[/bold cyan] verify all enabled")
            console.print("[bold cyan]2.[/bold cyan] verify specific")
            v_choice = Prompt.ask("choose", choices=["1", "2"], default="1")
            to_verify = []
            if v_choice == "1":
                to_verify = [(i, a) for i, a in enumerate(accounts) if a.get("enabled", True)]
            else:
                idx = int(Prompt.ask("no.", default="1")) - 1
                if 0 <= idx < len(accounts):
                    to_verify = [(idx, accounts[idx])]
            if not to_verify:
                console.print("[yellow]no accounts to verify.[/yellow]")
                time.sleep(1)
                continue
            for idx, acc in to_verify:
                name = acc.get("name", f"account{idx+1}")
                proxy_url, proxy_auth, proxy_label = engine.resolve_account_proxy(acc)
                with console.status(f"[cyan]verifying {name} ({proxy_label})..."):
                    try:
                        valid, user, v_channels = await engine.verify_token(
                            acc["token"], acc.get("channels", []), proxy_url, proxy_auth
                        )
                    except Exception as e:
                        valid, user, v_channels = False, str(e), []
                if valid:
                    console.print(f"[green]✓ {name}: verified as {user}[/green]")
                    if v_channels:
                        acc["channels"] = v_channels
                        engine.save_accounts(accounts)
                else:
                    console.print(f"[red]✗ {name}: verification failed ({user})[/red]")
            input("\nverification done. press enter.")
        elif action == "5":
            console.print("[dim]provide token file and channel file.[/dim]")
            token_file = Prompt.ask("path to token file (one token per line)")
            if not os.path.exists(token_file):
                console.print("[red]file not found.[/red]")
                time.sleep(1)
                continue
            with open(token_file, "r", encoding="utf-8") as f:
                tokens = [line.strip() for line in f if line.strip()]
            channel_file = Prompt.ask("path to channel file (space separated per line)")
            all_channels = []
            if os.path.exists(channel_file):
                with open(channel_file, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            all_channels.extend(parts)
            else:
                console.print("[yellow]channel file not found – will use empty list.[/yellow]")
            proxy_id = _pick_proxy()
            added = 0
            for i, tk in enumerate(tokens):
                name = f"acc{i+1}"
                accounts.append({
                    "name": name,
                    "token": tk,
                    "channels": all_channels.copy(),
                    "enabled": True,
                    "proxy_id": proxy_id,
                })
                added += 1
            engine.save_accounts(accounts)
            console.print(f"[green]{added} accounts imported.[/green]")
            time.sleep(1)
        else:
            break

def show_proxies_table():
    proxies = engine.load_proxies()
    if not proxies:
        console.print("[dim]no proxies in pool.[/dim]")
        return
    table = Table(border_style="cyan")
    table.add_column("no.", justify="center")
    table.add_column("label")
    table.add_column("type")
    table.add_column("endpoint")
    table.add_column("status")
    table.add_column("assigned")
    for idx, p in enumerate(proxies, 1):
        status = p.get("status", "unknown")
        color = "green" if status == "ok" else ("red" if status == "fail" else "yellow")
        table.add_row(
            str(idx),
            p.get("label", ""),
            p.get("type", "socks5"),
            f"{p.get('host')}:{p.get('port')}",
            f"[{color}]{status}[/{color}]",
            p.get("assigned_to") or "-",
        )
    console.print(table)

async def proxy_manager_cli(bulk_only=False):
    while True:
        show_banner('setup', animate=False)
        console.print("[bold white] proxy management [/bold white]\n")
        show_proxies_table()
        if bulk_only:
            console.print("\n[dim]paste proxies (one per line). empty line to finish:[/dim]")
            lines = []
            while True:
                line = Prompt.ask("proxy", default="")
                if not line:
                    break
                lines.append(line)
            if lines:
                result = engine.bulk_import_proxies("\n".join(lines))
                console.print(f"[green]added {len(result['added'])} proxies.[/green]")
                if result["errors"]:
                    console.print(f"[yellow]{len(result['errors'])} lines had errors.[/yellow]")
            return
        console.print(
            "\n[1] add single  [2] bulk import  [3] test all  [4] test one  [5] auto‑assign  [6] remove  [7] back"
        )
        action = Prompt.ask("action", choices=["1", "2", "3", "4", "5", "6", "7"], default="7")
        if action == "1":
            line = Prompt.ask("proxy (host:port)")
            proxy, err = engine.parse_proxy_line(line)
            if err and err != "empty":
                console.print(f"[red]invalid: {err}[/red]")
            elif proxy:
                proxies = engine.load_proxies()
                proxies.append(proxy)
                engine.save_proxies(proxies)
                console.print("[green]proxy added.[/green]")
            time.sleep(1)
        elif action == "2":
            console.print("[dim]paste proxies below. type END on its own line to finish:[/dim]")
            lines = []
            while True:
                line = input()
                if line.strip().upper() == "END":
                    break
                lines.append(line)
            result = engine.bulk_import_proxies("\n".join(lines))
            console.print(f"[green]added {len(result['added'])} proxies.[/green]")
            if result["errors"]:
                console.print(f"[yellow]{len(result['errors'])} lines had errors.[/yellow]")
            input("press enter...")
        elif action == "3":
            with console.status("[cyan]testing all proxies..."):
                results = await engine.test_all_proxies()
            ok = sum(1 for r in results if r.get("ok"))
            console.print(f"[green]{ok}/{len(results)} proxies ok[/green]")
            input("press enter...")
        elif action == "4":
            proxies = engine.load_proxies()
            if not proxies:
                continue
            idx = int(Prompt.ask("proxy no.", default="1")) - 1
            if 0 <= idx < len(proxies):
                with console.status("[cyan]testing..."):
                    ok = await engine.test_proxy(proxies[idx])
                    engine.save_proxies(proxies)
                console.print("[green]ok[/green]" if ok else "[red]fail[/red]")
            input("press enter...")
        elif action == "5":
            assigned = engine.auto_assign_proxies()
            console.print(f"[green]assigned {len(assigned)} proxy/account pairs.[/green]")
            time.sleep(1)
        elif action == "6":
            proxies = engine.load_proxies()
            if not proxies:
                continue
            idx = int(Prompt.ask("proxy no. to remove", default="1")) - 1
            if 0 <= idx < len(proxies):
                engine.remove_proxy(proxies[idx]["id"])
                console.print("[red]removed.[/red]")
            time.sleep(1)
        else:
            break

async def setup_menu():
    while True:
        show_banner('setup', animate=True)
        console.print(" [bold cyan]1.[/bold cyan] quick start [green](setup + launch)[/green]")
        console.print(" [bold cyan]2.[/bold cyan] manage accounts")
        console.print(" [bold cyan]3.[/bold cyan] manage proxies")
        console.print(" [bold cyan]4.[/bold cyan] repair environment")
        console.print(" [bold cyan]5.[/bold cyan] view setup log")
        console.print(" [bold cyan]6.[/bold cyan] exit")
        choice = Prompt.ask("choose", choices=["1", "2", "3", "4", "5", "6"], default="1")
        if choice == "1":
            ok = engine.run_full_setup()
            if not ok:
                input("\nsetup had errors. press enter to return.")
                continue
            accounts = engine.load_accounts()
            if not accounts:
                if Confirm.ask("no accounts. add one now?", default=True):
                    await account_manager(add_only=True)
            auth_path = os.path.join(state.CONFIG_DIR, "auth.json")
            try:
                with open(auth_path, "r", encoding="utf-8") as f:
                    auth = json.load(f)
                if auth.get("password") == "yuleeself_default_password_change_me":
                    if Confirm.ask("change default dashboard password?", default=False):
                        new_pass = Prompt.ask("new password", password=True)
                        if new_pass:
                            auth["password"] = new_pass
                            with open(auth_path, "w", encoding="utf-8") as f:
                                json.dump(auth, f, indent=4)
                            console.print("[green]password updated.[/green]")
            except Exception:
                pass
            proxies = engine.load_proxies()
            if not proxies:
                if Confirm.ask("import proxies now? (optional)", default=False):
                    await proxy_manager_cli(bulk_only=True)
            console.print("\n[green]launching YULEESELF...[/green]")
            time.sleep(1)
            import yulee
            await yulee.main()
            break
        elif choice == "2":
            await account_manager()
        elif choice == "3":
            await proxy_manager_cli()
        elif choice == "4":
            engine.run_full_setup(force_bootstrap=True)
            input("\nrepair finished. press enter.")
        elif choice == "5":
            if os.path.exists(engine.SETUP_LOG):
                with open(engine.SETUP_LOG, "r", encoding="utf-8") as f:
                    console.print(f.read())
            else:
                console.print("[dim]no setup log yet.[/dim]")
            input("\npress enter...")
        else:
            console.print("\n[magenta]thank you for using YULEESELF.[/magenta]")
            break

async def quick_start():
    console.print("[bold cyan]Quick start – setting up and launching...[/bold cyan]")
    ok = engine.run_full_setup()
    if not ok:
        console.print("[red]Setup failed. Please run without --quick to troubleshoot.[/red]")
        return
    accounts = engine.load_accounts()
    if not accounts:
        console.print("[yellow]No accounts found. Please add at least one account.[/yellow]")
        await account_manager(add_only=True)
        accounts = engine.load_accounts()
        if not accounts:
            console.print("[red]No accounts added. Cannot launch.[/red]")
            return
    proxies = engine.load_proxies()
    if not proxies:
        console.print("[yellow]No proxies found. You can run without proxies (direct connection).[/yellow]")
    console.print("[green]Launching YULEESELF...[/green]")
    import yulee
    await yulee.main()

def main():
    parser = argparse.ArgumentParser(description="YULEESELF Setup")
    parser.add_argument("--quick", action="store_true", help="Run quick setup and launch bot")
    parser.add_argument("--setup-only", action="store_true", help="Run setup only (no launch)")
    args = parser.parse_args()

    try:
        import rich
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "rich"], capture_output=True)

    if not engine.environment_healthy():
        engine.run_full_setup(force_bootstrap=True)

    if args.quick:
        asyncio.run(quick_start())
    elif args.setup_only:
        console.print("[green]Setup completed.[/green]")
        sys.exit(0)
    else:
        asyncio.run(setup_menu())

if __name__ == "__main__":
    main()