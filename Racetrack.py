from Obj3D import *
from Racecar import *
from Terrain import *
from Powerup import *

class Wall(Obj3D):
    def __init__(self, gameObj, model, renderParent=None, pos=None, hpr=None):
        super().__init__(model, renderParent, pos, hpr)
        self.gameObj = gameObj

        if "crate" in model: 
            self.scaleAll(0.01)

        #self.initTexture("concrete")

        self.repositionToCenter()
        self.move(dz=self.dimZ/2)

        args = {
            "padding": (0, 0, 0)
        }

        self.initSurroundingCollisionObj("wall", args=args)
        
        colNode = self.getCollisionNode("wall")
        colNode.node().setIntoCollideMask(self.gameObj.colBitMask["wall"])


'''
Class holds all walls and floors
'''
class Racetrack(Obj3D):
    def __init__(self, gameObj, trackName="test.track"):
        self.gameObj = gameObj
        self.wallType = "concrete_crate"

        # Get wall dimensions through a temporary wall
        tempWall = Wall(self.gameObj, self.wallType)
        self.wallDim = tempWall.getDimensions()
        self.wallOffset = tempWall.getOffset()
        tempWall.destroy()

        # Get racecar dimensions through a temporary car
        tempCar = Racecar(self.gameObj, "groundroamer")
        tempCarDim = tempCar.getDimensions()
        tempCar.destroy()
        Racecar.nRacecars -= 1

        # Set wall spacing
        self.defaultWallSpacing = max(self.wallDim) + tempCarDim[0] * 5

        # Generate racetrack
        self.points = []
        self.generateRacetrackFromFile(trackName)

        # Generate checkpoints
        self.checkpoints = []
        self.generateCheckpoints()

        # Generate powerups
        self.powerupSpawnChance = 0.5
        self.powerups = []
        self.generatePowerups()
    
    # Generate checkpoints
    # Basically collision boxes from left to right side point
    def generateCheckpoints(self):
        leftTrackPoints = self.leftTrackPoints
        rightTrackPoints = self.rightTrackPoints

        checkPointRad = self.wallDim[1]

        for i in range(len(leftTrackPoints)):
            leftPos, _ = leftTrackPoints[i]
            rightPos, _ = rightTrackPoints[i]

            x0, y0, z0 = leftPos
            x1, y1, z1 = rightPos

            colBox = CollisionCapsule(
                (x0, y0, z0),
                (x1, y1, z1),
                checkPointRad
            )

            colNode = Obj3D.createIsolatedCollisionObj(
                "checkpoint", colBox, intoBitmask=self.gameObj.colBitMask["checkpoint"],
                show=False
            )

            colNode.setPythonTag("checkpointID", i)

        return

    def generatePowerups(self):
        N = len(self.points)
        for i in range(N):
            if random.random() > self.powerupSpawnChance:
                continue

            point1 = LVector3f(self.points[i])
            point2 = LVector3f(self.points[(i+1) % N])

            dirVec = point2 - point1
            r = random.uniform(0.1, 0.9)

            pos = tuple(point1 + dirVec * r)

            powerup = ActivePowerup(self.gameObj, pos=pos)

            self.powerups.append(powerup)

        return

    # Parse the special race track file
    # Ignore comments which start with #
    # Returns a list of tuples of points
    # Includes the end point as the start point if necessary (need to close the loop)
    @staticmethod
    def parseTrackFile(fileName):
        points = []

        try:
            f = open(f"racetracks/{fileName}", "r")
        except:
            print(f"Racetrack {fileName} not found, defaulting to test.track")
            f = open(f"racetracks/test.track", "r")

        lineNo = 0
        for line in f:
            lineNo += 1
            # Remove away comments
            line = re.sub(r"\#(.+)", "", line).strip()

            # Ignore empty lines
            if len(line) == 0: 
                continue
            
            point = line.split(" ")
            # z-coordinate missing
            # default to 0
            if len(point) == 2:
                point.append(0)
            elif len(point) != 3:
                raise Exception(f"Invalid format in line {lineNo} of {fileName}.track")

            for i, coord in enumerate(point):
                try:
                    point[i] = float(coord)
                except:
                    raise Exception(f"Invalid format in line {lineNo} of {fileName}.track")

            points.append(tuple(point))

        # Handle useless points
        if points[0] == points[-1]:
            points.pop()

        for i in range(len(points)-2, 0, -1):
            # Check if direction vectors are parallel
            dir1 = LVector3f(points[i]) - LVector3f(points[i-1])
            dir2 = LVector3f(points[i]) - LVector3f(points[i+1])

            dir1.normalize()
            dir2.normalize()

            # Vectors are parallel, remove them otherwise they'll cause problems
            if dir1.cross(dir2) == LVector3f.zero():
                points.pop(i)

            continue

        if len(points) <= 3:
            raise Exception(f"{fileName}.track: Not enough points to make a racetrack!")

        f.close()
        return points

    # Generate racetrack given fileName of track
    def generateRacetrackFromFile(self, fileName):
        points = Racetrack.parseTrackFile(fileName)

        # line: (startPoint, dirVector)
        # sideTrack: (sidetrackPoint1, sideTrack2, angles)
        N = len(points)

        leftTrackPoints = []
        rightTrackPoints = []

        # Find bounds of inner and outer tracks
        for i in range(N):
            point = points[i]

            dir1 = sub2Tuples(points[i-1], point)
            dir2 = sub2Tuples(points[(i+1) % N], point)

            # Remember to swap positions due to the way the points are calculated!
            p1a, p1b, _ = self.calculateSideTracks((point, dir1))
            p2b, p2a, angles = self.calculateSideTracks((point, dir2))

            # Left track
            sideLine1 = (p1a, dir1)
            sideLine2 = (p2a, dir2)
            pos = intersectionOfLines(sideLine1, sideLine2)

            leftTrackPoints.append((pos, angles))

            # Right track
            sideLine1 = (p1b, multiplyVectorByScalar(dir1, -1))
            sideLine2 = (p2b, multiplyVectorByScalar(dir2, -1))
            pos = intersectionOfLines(sideLine1, sideLine2)

            rightTrackPoints.append((pos, angles))
        
        # Now actually generate the tracks!
        for i in range(N):
            # Left Track
            p0, angles = leftTrackPoints[i]
            p1, _ = leftTrackPoints[(i+1) % N]

            self.genWallsFromPointToPoint(p0, p1, angles)

            # Right Track
            p0, angles = rightTrackPoints[i]
            p1, _ = rightTrackPoints[(i+1) % N]

            self.genWallsFromPointToPoint(p0, p1, angles)

        self.points = points
        self.leftTrackPoints = leftTrackPoints
        self.rightTrackPoints = rightTrackPoints

        return

    def genWallsFromPointToPoint(self, startPoint, endPoint, angles=None):
        if angles == None: angles = (0, 0)
        thetha, phi = angles

        directionVector = sub2Tuples(endPoint, startPoint)
        distance = getVectorMagnitude(directionVector)

        if distance == 0: return

        # Walls needed to fill in the gap
        wallSize = self.wallDim[1]
        nWallsNeeded = math.ceil(distance / wallSize)

        for i in range(nWallsNeeded):
            pos = add2Tuples(
                startPoint, 
                multiplyVectorByScalar(directionVector, i * wallSize/distance)
            )
            wall = Wall(self.gameObj, self.wallType, pos=pos)
            wall.rotate(dh=thetha, dp=phi)

            # Generate floor from point to point as well
            ground = Ground(self.gameObj, "ground", pos=pos)
            ground.rotate(dh=thetha, dp=phi)


    # Given a start pos, calculate positions of side track points with defined spacing from the center position
    # and with the correct facing (yaw) 
    # Returns pos1, pos2, (thetha, phi) 
    def calculateSideTracks(self, line, spacing=None):
        startPos, directionVector = line

        spacing = self.defaultWallSpacing if spacing == None else spacing

        directionVector = normaliseVector(directionVector)
        if directionVector == (0, 0, 0): return

        x, y, z = startPos
        directionVector = multiplyVectorByScalar(directionVector, spacing/2)
        a, b, c = directionVector

        pos1 = x - b, y + a, z
        pos2 = x + b, y - a, z

        try:
            thetha = -radToDeg(math.atan(a/b))
        except:
            thetha = 0 

        # Fix the z angle component
        try:
            r = math.sqrt(a**2 + b**2)
            phi = radToDeg(math.atan(c/r))
        except:
            phi = 0

        return pos1, pos2, (thetha, phi)

    def drawMinimap(self):
        #https: // www.panda3d.org/reference/python/classpanda3d_1_1core_1_1LineSegs.html
        return
