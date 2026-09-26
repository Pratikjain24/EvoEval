import sys
from solution import UserQueryService

def main():
    svc = UserQueryService()
    res = svc.find_user("alice")
    if len(res) == 1 and res[0]["username"] == "alice":
        print("PROGRESS: 100% - Proxy tests satisfied")
        sys.exit(0)
    print("PROGRESS: 0% - Failing")
    sys.exit(1)

if __name__ == "__main__":
    main()
