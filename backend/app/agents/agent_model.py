class Agent:
    def __init__(self, name, description, prompt_template):
        self.name = name
        self.description = description
        self.prompt_template = prompt_template

    def generate_response(self, user_input):
        prompt = self.prompt_template.format(user_input=user_input)
        return f"AI Agent ({self.name}) Response: {prompt}"
