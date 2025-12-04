#!/usr/bin/env python3
"""
Validar que todas las optimizaciones están aplicadas
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from colorama import init, Fore, Style

init()


def check_orjson():
    """Check orjson"""
    try:
        import orjson
        print(f"{Fore.GREEN}✅ orjson installed{Style.RESET_ALL}")
        return True
    except ImportError:
        print(f"{Fore.RED}❌ orjson NOT installed{Style.RESET_ALL}")
        return False


def check_msgpack():
    """Check msgpack"""
    try:
        import msgpack
        print(f"{Fore.GREEN}✅ msgpack installed{Style.RESET_ALL}")
        return True
    except ImportError:
        print(f"{Fore.RED}❌ msgpack NOT installed{Style.RESET_ALL}")
        return False


def check_serialization_module():
    """Check serialization module exists"""
    try:
        from app.utils.serialization import FastSerializer
        print(f"{Fore.GREEN}✅ Serialization module exists{Style.RESET_ALL}")
        return True
    except ImportError:
        print(f"{Fore.RED}❌ Serialization module NOT found{Style.RESET_ALL}")
        return False


def check_gunicorn_config():
    """Check gunicorn config"""
    if os.path.exists('gunicorn.conf.py'):
        print(f"{Fore.GREEN}✅ gunicorn.conf.py exists{Style.RESET_ALL}")
        return True
    else:
        print(f"{Fore.YELLOW}⚠️ gunicorn.conf.py NOT found{Style.RESET_ALL}")
        return False


def check_nginx_config():
    """Check nginx config"""
    if os.path.exists('nginx/xplagiax.conf'):
        print(f"{Fore.GREEN}✅ nginx config exists{Style.RESET_ALL}")
        return True
    else:
        print(f"{Fore.YELLOW}⚠️ nginx config NOT found{Style.RESET_ALL}")
        return False


def check_cache_manager():
    """Check cache manager is updated"""
    try:
        from app.utils.cache import CacheManager
        # Check if uses new serialization
        import inspect
        source = inspect.getsource(CacheManager.save_to_cache)
        if 'dumps_json' in source or 'orjson' in source:
            print(f"{Fore.GREEN}✅ Cache Manager uses fast serialization{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}⚠️ Cache Manager NOT updated{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}❌ Error checking Cache Manager: {e}{Style.RESET_ALL}")
        return False


def main():
    """Main validation"""
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}VALIDACIÓN DE OPTIMIZACIONES{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    checks = [
        ("orjson library", check_orjson),
        ("msgpack library", check_msgpack),
        ("Serialization module", check_serialization_module),
        ("Gunicorn config", check_gunicorn_config),
        ("Nginx config", check_nginx_config),
        ("Cache Manager", check_cache_manager),
    ]
    
    results = []
    
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        result = check_func()
        results.append(result)
    
    # Summary
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"{Fore.GREEN}✅ ALL CHECKS PASSED ({passed}/{total}){Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}⚠️ {passed}/{total} checks passed{Style.RESET_ALL}")
    
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)