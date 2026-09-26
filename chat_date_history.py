import json
import anthropic
from pymongo import MongoClient
import sys
from datetime import datetime

class ClaudeChatClass:
    #chat_path is path to Claude JSON
    def __init__(self, chat_path):
        self.claude_chat_json = json.load(open(chat_path))
        self.date_to_chat = self._get_frequencies(True)
        self.chat_to_date = self._get_frequencies(False)
        
    # Returns nested dictionary of message lists grouped by two keys.
    # group_by_date=True -> {date: {chat_name: [messages]}}
    # group_by_date=False -> {chat_name: {date: [messages]}}
    def _get_frequencies(self, group_by_date=True):

        result = {}

        for chat in self.claude_chat_json:
            cur_chat_messages = chat["chat_messages"]
            chat_name = chat["name"]
            for cur_message in cur_chat_messages:
                cur_date = cur_message["created_at"][:10]
                outer_key, inner_key = (cur_date, chat_name) if group_by_date else (chat_name, cur_date)
                #checking if current date/current chat is already key in result. If not then add it to result
                if outer_key not in result:
                    result[outer_key] = {}
                #checking if current chat/current date is already in result[current date] or result[current chat] respectively
                if inner_key not in result[outer_key]:
                    result[outer_key][inner_key] = []
                #TODO should this be cur_message or cur_message["text"]?
                result[outer_key][inner_key].append(cur_message)
        return result
    
    def summarize_chats_on_date(self, date="2025-09-01"):
        if date not in self.date_to_chat:
            print(f"No chats found for {date}")
            return None

        #dictionary containing only chats for date
        chats_on_date = self.date_to_chat[date]
        # Build a text block listing each chat and its messages for that date
        chat_text = ""
        for chat_name, messages in chats_on_date.items():
            chat_text += f"\n--- Chat: {chat_name} ---\n"
            #need json.dumps for dictionary to string conversion
            for msg in messages:
                chat_text += f"  {json.dumps(msg)}\n"
        #Keeping Claude key in separate file of course
        api_key = open("claude_api_key.txt").read().strip()
        client = anthropic.Anthropic(api_key=api_key)
        #Using Haiku because summarizing is a really basic task
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"Here are my Claude chats from {date}. Please give a brief summary of what I talked about with Claude on that date. Each message is in JSON format and therefore contains the text of the message, \
                    the role of the message (user or assistant) and the exact time that the chat was sent.\n\n{chat_text}"
            }]
        )
        summary = response.content[0].text
        print(summary)
        return summary



if __name__ == "__main__":
    claude_obj = ClaudeChatClass('./conversations.json')
    date_to_chat = claude_obj._get_frequencies(group_by_date=True)
    chat_to_date = claude_obj._get_frequencies(group_by_date=False)
    print('\n\n\n\n')
    #sys.argv[1] is outer key
    if sys.argv[1] == "date":
        date = datetime.strptime(sys.argv[2], "%Y-%m-%d").strftime("%Y-%m-%d")
        #List of tuples where tup(0) is chat name, tup(1) is number of times that chat was used on said date
        info = [(chat_name, len(date_to_chat[date][chat_name])) for chat_name in list(date_to_chat[date])]
        #First sort the list of tuples by the second element of the tuple (number of times the chat was used on said date)
        #For some reason some chats are empty, so we filter them out
        print(list(filter(lambda x: x[0] != "", sorted(info, key=lambda x: x[1], reverse=True))))

    elif sys.argv[1] == "chat":
        chat_name = sys.argv[2]
        #List of tuples where tup(0) is date, tup(1) is number of times that chat was used on said date
        info = [(date, len(chat_to_date[chat_name][date])) for date in list(chat_to_date[chat_name])]
        #Don't need to do any filtering because dates can't be empty
        print(list(sorted(info, key=lambda x: x[1], reverse=True)))
    else:
        raise ValueError("Invalid argument: sys.argv[1] must be 'date' or 'chat'")