class User:
    def __init__(self, name, color):
        self.name = name
        self.color = color

class UserPool:
    def __init__(self):

        self.users = {}
        self.path = "./.avis_users"

        import os.path
        if os.path.isfile(self.path):
            f = file(self.path,'r')
        else:
            f = None

        if not f is None:
            name = ""
            color = (1.0, 0.0, 0.0)

            lines = f.readlines()
            tokens = []
            for l in lines:
                t = l.split()
                tokens += t

            i = 0
            while (i < len(tokens)):
                if tokens[i] == "user":
                    pass
                elif tokens[i] == "name":
                    i += 1
                    name = tokens[i]
                elif tokens[i] == "color":
                    color = (float(tokens[i+1]), float(tokens[i+2]), float(tokens[i+3]))
                    i += 3
                elif tokens[i] == "end_user":
                    u = User(name, color)
                    self.users[u.name] = u
                    name = ""
                    color = (1.0, 0.0, 0.0)
                i += 1        

            f.close()

    def __del__(self):
        lines = []
        for user in self.users:
            lines.append("user\n")
            lines.append("   name " + self.users[user].name+"\n")
            lines.append("   color " + 
                         str(self.users[user].color[0]) + " " + 
                         str(self.users[user].color[1]) + " " + 
                         str(self.users[user].color[2]) + "\n")
            lines.append("end_user\n")

        f = file(self.path, 'w')
        f.writelines(lines)
        f.close()
            
    def queryUser(self, user):
        return self.users.has_key(user)

    def addUser(self, user):
        print "Added user", user.name
        self.users[user.name] = user
