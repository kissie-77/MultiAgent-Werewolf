import seerImg from "../../public/material/seer.png";
import witchImg from "../../public/material/witch.png";
import hunterImg from "../../public/material/hunter.png";
import wolfImg from "../../public/material/wolf.png";
import villagerImg from "../../public/material/villiger.png";

export const roleImageMap: Record<string, string> = {
  "预言家": seerImg,
  "女巫": witchImg,
  "猎人": hunterImg,
  "狼人": wolfImg,
  "狼王": wolfImg,
  "白狼": wolfImg,
  "狼美人": wolfImg,
  "守卫狼": wolfImg,
  "隐狼": wolfImg,
  "血月使徒": wolfImg,
  "梦魇狼": wolfImg,
  "守卫": villagerImg,
  "白痴": villagerImg,
  "长老": villagerImg,
  "骑士": villagerImg,
  "魔术师": villagerImg,
  "丘比特": villagerImg,
  "乌鸦": villagerImg,
  "守墓人": villagerImg,
  "盗贼": villagerImg,
  "恋人": villagerImg,
  "村民": villagerImg,
  "平民": villagerImg,
};

export const getRoleImage = (role: string) => {
  return roleImageMap[role] || villagerImg;
};
