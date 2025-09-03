from presentations.app import app
import uvicorn

def main() -> None:
    uvicorn.run(app)

if __name__ == "__main__":
    main()
