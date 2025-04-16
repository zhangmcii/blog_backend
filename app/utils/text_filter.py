class DFAFilter():
    '''Filter Messages from keywords

    Use DFA to keep algorithm perform constantly

    hello **** baby
    '''

    def __init__(self):
        self.keyword_chains = {}
        self.delimit = '\x00'
        self.parse("app/utils/keywords")

    def add(self, keyword):
        # if not isinstance(keyword, unicode):
        #     keyword = keyword.decode('utf-8')
        keyword = keyword.lower()
        chars = keyword.strip()
        if not chars:
            return
        level = self.keyword_chains
        for i in range(len(chars)):
            if chars[i] in level:
                level = level[chars[i]]
            else:
                if not isinstance(level, dict):
                    break
                for j in range(i, len(chars)):
                    level[chars[j]] = {}
                    last_level, last_char = level, chars[j]
                    level = level[chars[j]]
                last_level[last_char] = {self.delimit: 0}
                break
        if i == len(chars) - 1:
            level[self.delimit] = 0

    def parse(self, path):
        with open(path, encoding='utf-8') as f:
            for keyword in f:
                self.add(keyword.strip())

    def filter(self, message, repl="*"):
        # if not isinstance(message, unicode):
        #     message = message.decode('utf-8')
        message = message.lower()
        ret = []
        start = 0
        while start < len(message):
            level = self.keyword_chains
            step_ins = 0
            for char in message[start:]:
                if char in level:
                    step_ins += 1
                    if self.delimit not in level[char]:
                        level = level[char]
                    else:
                        ret.append(repl * step_ins)
                        start += step_ins - 1
                        break
                else:
                    ret.append(message[start])
                    break
            else:
                ret.append(message[start])
            start += 1

        return ''.join(ret)

gfw = DFAFilter()

def first_character():
    gfw = DFAFilter()
    gfw.add("1989年")
    assert gfw.filter("1989", "*") == "1989"


if __name__ == "__main__":
    # gfw = NaiveFilter()
    # gfw = BSFilter()
    gfw = DFAFilter()
    gfw.parse("keywords")
    import time

    t = time.time()
    # print(gfw.filter("法轮功 我操操操", "*"))
    # print( gfw.filter("针孔摄像机 我操操操", "*"))
    # print( gfw.filter("售假人民币 我操操操", "*"))
    # print( gfw.filter("传世私服 我操操操", "*"))

    print(gfw.filter("shabi", "*"))
    print(time.time() - t)
    first_character()
