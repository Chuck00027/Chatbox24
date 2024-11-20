# Chatbox24
Load the conversation history of the email. Generate automatic answers based on RAG. Can be tested and trained locally. In the future, it can be run on the server and automatically reply to email inquiries.

The basic RAG answer generation function is implemented, but the function of processing loaded emails still needs to be optimized. loadfile.py reads the relevant regulations and stores the content in Knowlege Base.txt. gmailload.py can read the selected email. raganswer-static.py can read the questions in questions.txt and generate answers. raganswer-dynamic.py is used for continuous questioning, and the actual work on the server when used simulates real continuous communication and answering

Preliminary preparation：
1.Please download Ollama: https://ollama.com/download
Then  run the command to install the models:
ollama pull llama3
ollama pull mxbai-embed-large

2.Set up a Gmail password：
Turn on 2-Step Verification in Google Security
Enable IMAP of Gmial
Then full your Email and password in env file

Then Setup：
1.cd dir
2.pip install -r requirements.txt
3.python loadfile.py
You could select the requirement documents to load into the Knowledge Base
4.run gmailload.py
You could load emails with specified labels, specified keywords, and specified time ranges.
e.g.    python gmailload.py --keyword "your_search_keyword" --startdate "01.01.2024" --enddate "31.01.2024" --label "your_label"
python gmailload.py --label "your_label"

In that way the Email conversation is loaded. The normalized text in stored in Knowledge Base.txt(Enhanced knowledge base,improve abaility) and Standard Q&A.txt(generalize the email conversation into Q&A form,use it as sample solution,could be used to test the accuracy of the RAG answer).BUT this function needs to be improved，to avoid noise information.
5.python raganswer-static.py
We should first edit the questions in question.txt.In that way the answer is generated and stored in answers.txt with Q&A form
6.To be implemented, use the newly obtained questions and old KB to test the accuracy of the answers
7.python raganswer-dynamic.py
In order to run on the server in the future. In multiple rounds of communication, combine the previous information to give further answers. Run this program, you can manually enter questions, and it will eliminate more accurate answers based on your multiple rounds of questions.

The next step will be to improve the current deficiencies and further integrate the program into the GUI interface
