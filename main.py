import subprocess

cmd = "echo Hello world"

result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    shell=True
)

print("stdout:", result.stdout)


print("Running program")


result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300,
                        # creationflags=True
                        # creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0
                    )
print("Result : ", result)

