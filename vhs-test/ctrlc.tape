Output ctrlc.txt
Set TypingSpeed 50ms
Set Shell bash

Type "sleep 10"
Enter
Sleep 500ms

# Should show sleep running
Screenshot before_ctrlc.png

# Send Ctrl+C
Ctrl+C
Sleep 500ms

# Should show command interrupted
Screenshot after_ctrlc.png
