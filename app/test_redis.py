from app.cache import redis_client


def main():
    try:
        redis_client.ping()
        print("✅ Redis ga ulandi!")
    except Exception as e:
        print(f"❌ Redis xato: {e}")


if __name__ == "__main__":
    main()
