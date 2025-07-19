def main():
    try:
        ### TO DO: Implement the main logic here ###
        raise Exception
    except:
        from fallback import agent_step
        from pathlib import Path
        project_root = Path(__file__).parent.resolve()
        ### If the mail agent falls, we will use the fallback agent ###
        agent_step(project_root, model="o3-ver1")


if __name__ == "__main__":
    main()
    #remove seed.txt
    from pathlib import Path
    seed_file = Path(__file__).parent / "seed.txt"
    if seed_file.is_file():
        seed_file.unlink()
