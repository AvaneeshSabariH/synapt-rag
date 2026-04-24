import sys
from agent.loop import run_agent

def main():
    print("Welcome to the Indian IT Company Financials RAG Agent!")
    print("Ask questions about Infosys, TCS, and Wipro.")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            question = input("\nYour question: ").strip()
            if not question:
                continue
            if question.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
                
            print(f"\nThinking...")
            result = run_agent(question)
            
            print("\n" + "=" * 60)
            print("ANSWER:")
            print(result["answer"])
            print("=" * 60 + "\n")
            
        except KeyboardInterrupt:
            print("\nInterrupted. Type 'exit' to quit.")
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
