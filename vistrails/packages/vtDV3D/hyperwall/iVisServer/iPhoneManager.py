class IPhoneManager:
    def __init__(self):
        pass
#        self.userPool = UserPool()

    def processMessage(self, message):
        tokens = message.split(',')
        if len(tokens) != 0:
            if tokens[0] == "tryConnect":
                return "iPhoneManager:acceptConnect"
            elif tokens[0] == "username":
                if self.userPool.queryUser(tokens[1]):
                    return "iPhoneManager:username,true,"\
                        +str(self.userPool.users[tokens[1]].color[0])+","\
                        +str(self.userPool.users[tokens[1]].color[1])+","\
                        +str(self.userPool.users[tokens[1]].color[2])
                else:
                    return "iPhoneManager:username,false"
            elif tokens[0] == "createUser":
                if not self.userPool.queryUser(tokens[1]):
                    name = tokens[1]
                    color = (float(tokens[2]),float(tokens[3]),float(tokens[4]))
                    u = User(name, color)
                    self.userPool.addUser(u)
                    return "iPhoneManager:createdUser,true"
                else:
                    return "iPhoneManager:createdUser,false"
            
        return ""
