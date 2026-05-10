from core.llm import Agent

TEST_USER_ID = "11111111-1111-1111-1111-111111111111"
TEST_SESSION_ID = "default"


def main():
    jarvis = Agent(session_id=TEST_SESSION_ID, user_id=TEST_USER_ID)
    jarvis.run()


if __name__ == "__main__":
    main()
